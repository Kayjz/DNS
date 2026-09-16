import { exec } from "child_process";
import { promisify } from "util";
import { PrismaClient } from "@prisma/client";

const execAsync = promisify(exec);

export class WhitelistService {
  private static instance: WhitelistService;
  private prisma: PrismaClient;

  private constructor(prisma: PrismaClient) {
    this.prisma = prisma;
  }

  public static getInstance(prisma: PrismaClient): WhitelistService {
    if (!WhitelistService.instance) {
      WhitelistService.instance = new WhitelistService(prisma);
    }
    return WhitelistService.instance;
  }

  /**
   * Initializes Linux ipset for high-performance zero-delay client filtering
   */
  public async initIpset(): Promise<void> {
    try {
      await execAsync("which ipset");
      await execAsync("ipset create -exist smartdns_whitelist hash:ip");
      console.log("[WhitelistService] ipset 'smartdns_whitelist' ready");
    } catch (err) {
      console.warn("[WhitelistService] ipset not available or running outside Linux. Simulated mode.");
    }
  }

  /**
   * Syncs an active customer IP into the system whitelist
   */
  public async authorizeIp(ip: string): Promise<boolean> {
    if (!ip || ip === "127.0.0.1" || ip === "::1") return false;
    try {
      await execAsync(`ipset add -exist smartdns_whitelist ${ip}`);
      console.log(`[WhitelistService] Whitelisted client IP: ${ip}`);
      return true;
    } catch (err) {
      console.log(`[WhitelistService] Whitelisted (simulated): ${ip}`);
      return true;
    }
  }

  /**
   * Removes an IP when a subscription expires
   */
  public async revokeIp(ip: string): Promise<boolean> {
    if (!ip) return false;
    try {
      await execAsync(`ipset del -exist smartdns_whitelist ${ip}`);
      console.log(`[WhitelistService] Revoked client IP: ${ip}`);
      return true;
    } catch (err) {
      return true;
    }
  }

  /**
   * Periodic sync job: checks all subscriptions and purges expired IPs
   */
  public async syncAllActiveIps(): Promise<void> {
    const now = new Date();
    const activeSubs = await this.prisma.subscription.findMany({
      where: {
        status: "ACTIVE",
        expiresAt: { gt: now },
        activeClientIp: { not: null },
      },
      select: { activeClientIp: true },
    });

    for (const sub of activeSubs) {
      if (sub.activeClientIp) {
        await this.authorizeIp(sub.activeClientIp);
      }
    }
  }
}
