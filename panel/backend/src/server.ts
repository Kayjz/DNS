import Fastify, { FastifyInstance, FastifyRequest, FastifyReply } from "fastify";
import cors from "@fastify/cors";
import jwt from "@fastify/jwt";
import multipart from "@fastify/multipart";
import { PrismaClient } from "@prisma/client";
import bcrypt from "bcrypt";
import { WhitelistService } from "./services/whitelist.service";

const prisma = new PrismaClient();
const whitelistService = WhitelistService.getInstance(prisma);

const server: FastifyInstance = Fastify({
  logger: true,
  trustProxy: true,
});

server.register(cors, {
  origin: true,
  credentials: true,
});

server.register(jwt, {
  secret: process.env.JWT_SECRET || "SUPER_SECRET_SMARTDNS_KEY_2026",
});

server.register(multipart, {
  limits: {
    fileSize: 10 * 1024 * 1024, // 10MB receipt max
  },
});

// Authentication Decorator
server.decorate("authenticate", async (request: FastifyRequest, reply: FastifyReply) => {
  try {
    await request.jwtVerify();
  } catch (err) {
    reply.status(401).send({ error: "Unauthorized access" });
  }
});

// Admin Authorization Decorator
server.decorate("requireAdmin", async (request: any, reply: FastifyReply) => {
  try {
    await request.jwtVerify();
    if (request.user.role !== "ADMIN") {
      return reply.status(403).send({ error: "Admin privilege required" });
    }
  } catch (err) {
    reply.status(401).send({ error: "Unauthorized access" });
  }
});

// -----------------------------------------------------------------------------
// 1. PUBLIC ROUTES
// -----------------------------------------------------------------------------

// Detect Client Public IP
server.get("/api/my-ip", async (req: FastifyRequest) => {
  const clientIp = req.headers["x-forwarded-for"] || req.socket.remoteAddress || "";
  const cleanIp = Array.isArray(clientIp) ? clientIp[0] : clientIp.split(",")[0].trim();
  return { ip: cleanIp };
});

// List Available Subscription Plans
server.get("/api/plans", async () => {
  return await prisma.plan.findMany({ where: { isActive: true } });
});

// User Registration
server.post("/api/auth/register", async (req: FastifyRequest, reply: FastifyReply) => {
  const { username, phoneOrEmail, password } = req.body as any;
  if (!username || !phoneOrEmail || !password) {
    return reply.status(400).send({ error: "All fields are required" });
  }

  const existing = await prisma.user.findFirst({
    where: { OR: [{ username }, { phoneOrEmail }] },
  });
  if (existing) {
    return reply.status(400).send({ error: "Username or Phone/Email already in use" });
  }

  const passwordHash = await bcrypt.hash(password, 10);
  
  // First user created automatically becomes ADMIN
  const userCount = await prisma.user.count();
  const role = userCount === 0 ? "ADMIN" : "CUSTOMER";

  const user = await prisma.user.create({
    data: { username, phoneOrEmail, passwordHash, role },
  });

  const token = server.jwt.sign({ id: user.id, username: user.username, role: user.role });
  return { token, user: { id: user.id, username: user.username, role: user.role } };
});

// User / Admin Login
server.post("/api/auth/login", async (req: FastifyRequest, reply: FastifyReply) => {
  const { loginIdentifier, password } = req.body as any;
  const user = await prisma.user.findFirst({
    where: { OR: [{ username: loginIdentifier }, { phoneOrEmail: loginIdentifier }] },
    include: { subscription: true },
  });

  if (!user || !(await bcrypt.compare(password, user.passwordHash))) {
    return reply.status(401).send({ error: "Invalid credentials" });
  }

  const token = server.jwt.sign({ id: user.id, username: user.username, role: user.role });
  return {
    token,
    user: {
      id: user.id,
      username: user.username,
      role: user.role,
      subscription: user.subscription,
    },
  };
});

// -----------------------------------------------------------------------------
// 2. CUSTOMER ROUTES
// -----------------------------------------------------------------------------

// Get Customer Profile & Subscription
server.get("/api/customer/profile", { preHandler: [(server as any).authenticate] }, async (req: any) => {
  return await prisma.user.findUnique({
    where: { id: req.user.id },
    include: { subscription: { include: { plan: true } }, receipts: { include: { plan: true } } },
  });
});

// 1-Click Update Client IP
server.post("/api/customer/sync-ip", { preHandler: [(server as any).authenticate] }, async (req: any, reply: FastifyReply) => {
  const user = await prisma.user.findUnique({
    where: { id: req.user.id },
    include: { subscription: true },
  });

  if (!user?.subscription || user.subscription.status !== "ACTIVE" || new Date(user.subscription.expiresAt) < new Date()) {
    return reply.status(403).send({ error: "No active subscription found" });
  }

  const clientIp = (req.body as any)?.ip || req.headers["x-forwarded-for"] || req.socket.remoteAddress || "";
  const cleanIp = Array.isArray(clientIp) ? clientIp[0] : clientIp.split(",")[0].trim();

  // Whitelist IP in Linux firewall
  await whitelistService.authorizeIp(cleanIp);

  const updatedSub = await prisma.subscription.update({
    where: { userId: user.id },
    data: {
      activeClientIp: cleanIp,
      lastIpSyncAt: new Date(),
    },
  });

  return { message: "IP successfully authorized for SmartDNS", ip: cleanIp, subscription: updatedSub };
});

// Submit Payment Receipt
server.post("/api/customer/submit-receipt", { preHandler: [(server as any).authenticate] }, async (req: any, reply: FastifyReply) => {
  const { planId, cardLastDigits, trackingRef, receiptImage } = req.body as any;
  if (!planId) return reply.status(400).send({ error: "Plan ID is required" });

  const receipt = await prisma.receipt.create({
    data: {
      userId: req.user.id,
      planId,
      cardLastDigits,
      trackingRef,
      receiptImage,
      status: "PENDING",
    },
  });

  return { message: "Receipt submitted! Awaiting admin approval.", receipt };
});

// -----------------------------------------------------------------------------
// 3. ADMIN ROUTES
// -----------------------------------------------------------------------------

// List All Customers & Subscriptions
server.get("/api/admin/users", { preHandler: [(server as any).requireAdmin] }, async () => {
  return await prisma.user.findMany({
    include: { subscription: { include: { plan: true } } },
    orderBy: { createdAt: "desc" },
  });
});

// List Receipts (Pending first)
server.get("/api/admin/receipts", { preHandler: [(server as any).requireAdmin] }, async () => {
  return await prisma.receipt.findMany({
    include: { user: true, plan: true },
    orderBy: { createdAt: "desc" },
  });
});

// Approve or Reject Receipt
server.post("/api/admin/receipts/:id/review", { preHandler: [(server as any).requireAdmin] }, async (req: any, reply: FastifyReply) => {
  const { id } = req.params;
  const { action, adminNote } = req.body as any; // action: "APPROVE" or "REJECT"

  const receipt = await prisma.receipt.findUnique({ where: { id }, include: { plan: true } });
  if (!receipt) return reply.status(404).send({ error: "Receipt not found" });

  if (action === "APPROVE") {
    const days = receipt.plan.durationDays;
    const now = new Date();
    const currentSub = await prisma.subscription.findUnique({ where: { userId: receipt.userId } });

    let newExpiresAt = new Date();
    if (currentSub && currentSub.expiresAt > now) {
      newExpiresAt = new Date(currentSub.expiresAt.getTime() + days * 24 * 60 * 60 * 1000);
    } else {
      newExpiresAt = new Date(now.getTime() + days * 24 * 60 * 60 * 1000);
    }

    await prisma.$transaction([
      prisma.receipt.update({
        where: { id },
        data: { status: "APPROVED", adminNote },
      }),
      prisma.subscription.upsert({
        where: { userId: receipt.userId },
        create: {
          userId: receipt.userId,
          planId: receipt.planId,
          status: "ACTIVE",
          expiresAt: newExpiresAt,
        },
        update: {
          planId: receipt.planId,
          status: "ACTIVE",
          expiresAt: newExpiresAt,
        },
      }),
    ]);

    return { message: `Receipt approved! User subscription extended by ${days} days.` };
  } else {
    await prisma.receipt.update({
      where: { id },
      data: { status: "REJECTED", adminNote },
    });
    return { message: "Receipt marked as rejected." };
  }
});

// Seed default plans if table is empty
async function seedDefaultPlans() {
  const count = await prisma.plan.count();
  if (count === 0) {
    await prisma.plan.createMany({
      data: [
        { name: "Starter Gaming Pass (30 Days)", durationDays: 30, priceToman: 79000, description: "Full console unblock, PS5/Xbox/EA, low ping" },
        { name: "Pro Gamer Pass (90 Days)", durationDays: 90, priceToman: 199000, description: "3 Months unlimited console + PC access" },
        { name: "Annual VIP Pass (365 Days)", durationDays: 365, priceToman: 590000, description: "1 Full year with VIP priority support" },
      ],
    });
    console.log("[Seed] Default gaming plans created.");
  }
}

// Start Server
const start = async () => {
  try {
    await whitelistService.initIpset();
    await seedDefaultPlans();
    
    // Background interval: sync IPs every 5 minutes
    setInterval(() => {
      whitelistService.syncAllActiveIps().catch(console.error);
    }, 5 * 60 * 1000);

    const port = Number(process.env.PORT) || 5000;
    await server.listen({ port, host: "0.0.0.0" });
    console.log(`[SmartDNS Backend API] running on http://0.0.0.0:${port}`);
  } catch (err) {
    server.log.error(err);
    process.exit(1);
  }
};

start();
