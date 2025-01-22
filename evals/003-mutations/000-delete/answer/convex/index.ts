import { v } from "convex/values";
import { mutation } from "./_generated/server";

export const deleteUserById = mutation({
  args: { id: v.id("users") },
  returns: v.null(),
  handler: async (ctx, args) => {
    await ctx.db.delete(args.id);
    return null;
  },
});
