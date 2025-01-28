import { v } from "convex/values";
import { query } from "./_generated/server";

export const getSensorReadingsInRange = query({
  args: {
    sensorId: v.string(),
    startTime: v.number(),
    endTime: v.number(),
  },
  returns: v.array(
    v.object({
      _id: v.id("temperatures"),
      _creationTime: v.number(),
      sensorId: v.string(),
      timestamp: v.number(), // Unix timestamp in seconds
      value: v.number(),
    })
  ),
  handler: async (ctx, args) => {
    return await ctx.db
      .query("temperatures")
      .withIndex("by_sensor_time", (q) =>
        q
          .eq("sensorId", args.sensorId)
          .gte("timestamp", args.startTime)
          .lte("timestamp", args.endTime)
      )
      .collect();
  },
});
