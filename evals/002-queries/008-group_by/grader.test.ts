import { expect, test } from "vitest";
import {
  responseAdminClient,
  responseClient,
  compareSchema,
  compareFunctionSpec,
  addDocuments,
} from "../../../grader";
import { anyApi } from "convex/server";

test("compare schema", async () => {
  await compareSchema();
});

test("compare function spec", async () => {
  await compareFunctionSpec();
});

test("get monthly sales by category returns empty array when no sales exist", async () => {
  const stats = await responseClient.query(anyApi.public.getMonthlySalesByCategory, {
    region: "west",
    month: "2024-01"
  });
  expect(stats).toEqual([]);
});

test("get monthly sales by category groups and sorts correctly", async () => {
  // Load test data with multiple categories and regions
  const testSales = [
    // West region, January 2024
    { region: "west", product: "laptop", category: "electronics", amount: 1200.00, date: "2024-01" },
    { region: "west", product: "phone", category: "electronics", amount: 800.00, date: "2024-01" },
    { region: "west", product: "desk", category: "furniture", amount: 500.00, date: "2024-01" },
    { region: "west", product: "chair", category: "furniture", amount: 300.00, date: "2024-01" },
    { region: "west", product: "book", category: "books", amount: 20.00, date: "2024-01" },

    // West region, different month
    { region: "west", product: "tablet", category: "electronics", amount: 600.00, date: "2024-02" },

    // Different region, same month
    { region: "east", product: "laptop", category: "electronics", amount: 1200.00, date: "2024-01" }
  ];
  await addDocuments(responseAdminClient, "sales", testSales);

  // Test west region, January 2024
  const westJanStats = await responseClient.query(anyApi.public.getMonthlySalesByCategory, {
    region: "west",
    month: "2024-01"
  });

  // Should be sorted by totalSales descending
  expect(westJanStats).toEqual([
    {
      category: "electronics",
      totalSales: 2000.00,
      averageSaleAmount: 1000.00,
      numberOfSales: 2
    },
    {
      category: "furniture",
      totalSales: 800.00,
      averageSaleAmount: 400.00,
      numberOfSales: 2
    },
    {
      category: "books",
      totalSales: 20.00,
      averageSaleAmount: 20.00,
      numberOfSales: 1
    }
  ]);

  // Test west region, February 2024
  const westFebStats = await responseClient.query(anyApi.public.getMonthlySalesByCategory, {
    region: "west",
    month: "2024-02"
  });

  expect(westFebStats).toEqual([
    {
      category: "electronics",
      totalSales: 600.00,
      averageSaleAmount: 600.00,
      numberOfSales: 1
    }
  ]);

  // Test east region, January 2024
  const eastJanStats = await responseClient.query(anyApi.public.getMonthlySalesByCategory, {
    region: "east",
    month: "2024-01"
  });

  expect(eastJanStats).toEqual([
    {
      category: "electronics",
      totalSales: 1200.00,
      averageSaleAmount: 1200.00,
      numberOfSales: 1
    }
  ]);
});

test("get monthly sales by category handles fractional amounts", async () => {
  // Load test data with fractional amounts
  const testSales = [
    { region: "north", product: "item1", category: "misc", amount: 10.99, date: "2024-01" },
    { region: "north", product: "item2", category: "misc", amount: 20.49, date: "2024-01" },
    { region: "north", product: "item3", category: "misc", amount: 15.33, date: "2024-01" }
  ];
  await addDocuments(responseAdminClient, "sales", testSales);

  const stats = await responseClient.query(anyApi.public.getMonthlySalesByCategory, {
    region: "north",
    month: "2024-01"
  });

  expect(stats).toEqual([
    {
      category: "misc",
      totalSales: 46.81,
      averageSaleAmount: 15.60,
      numberOfSales: 3
    }
  ]);
});

