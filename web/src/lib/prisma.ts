import { PrismaClient } from '@/generated/prisma';

const globalForPrisma = globalThis as unknown as {
  prisma: PrismaClient | undefined;
};

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const db = globalForPrisma.prisma ?? new (PrismaClient as any)();

if (process.env.NODE_ENV !== 'production') globalForPrisma.prisma = db;

export default db;
