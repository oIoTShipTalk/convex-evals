import { v } from "convex/values";
import { query } from "./_generated/server";

export const getProjectTasksByStatus = query({
  args: {
    projectId: v.string(),
    status: v.string(),
  },
  returns: v.array(
    v.object({
      _id: v.id("tasks"),
      _creationTime: v.number(),
      projectId: v.string(),
      status: v.string(),
      priority: v.number(),
      title: v.string(),
      assignee: v.string(),
    })
  ),
  handler: async (ctx, args) => {
    return await ctx.db
      .query("tasks")
      .withIndex("by_project_status_priority", (q) =>
        q.eq("projectId", args.projectId).eq("status", args.status)
      )
      .take(5);
  },
});
