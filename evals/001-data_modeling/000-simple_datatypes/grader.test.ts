import { expect, test } from "vitest";
import { compareFunctionSpec, compareSchema } from "../../../grader";

test("compare schema", async ({ skip }) => {
  await compareSchema(skip);
});

test("compare function spec", async ({ skip }) => {
  await compareFunctionSpec(skip);
});
