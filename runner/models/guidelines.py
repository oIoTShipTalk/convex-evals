class Guideline:
    def __init__(self, content: str):
        self.content = content.strip()


class GuidelineSection:
    def __init__(self, name: str, children: list):
        self.name = name
        self.children = children


CONVEX_GUIDELINES = GuidelineSection(
    "convex_guidelines",
    [
        GuidelineSection(
            "function_guidelines",
            [
                GuidelineSection(
                    "new_function_syntax",
                    [
                        Guideline(
                            """
      ALWAYS use the new function syntax for Convex functions. For example:
      ```typescript
      import { query } from "./_generated/server";
      import { v } from "convex/values";
      export const f = query({
          args: {},
          returns: v.null(),
          handler: async (ctx, args) => {
          // Function body
          },
      });
      ```
      """
                        ),
                    ],
                ),
                GuidelineSection(
                    "http_endpoint_syntax",
                    [
                        Guideline(
                            """
      HTTP endpoints are defined in `convex/http.ts` and require an `httpAction` decorator. For example:
      ```typescript
      import { httpRouter } from "convex/server";
      import { httpAction } from "./_generated/server";
      const http = httpRouter();
      http.route({
          path: "/echo",
          method: "POST",
          handler: httpAction(async (ctx, req) => {
          const body = await req.bytes();
          return new Response(body, { status: 200 });
          }),
      });
      ```
      """
                        ),
                    ],
                ),
                GuidelineSection(
                    "function_registration",
                    [
                        Guideline(
                            "Use `internalQuery`, `internalMutation`, and `internalAction` to register internal functions. These functions are private and aren't part of an app's API. They can only be called by other Convex functions."
                        ),
                        Guideline(
                            "Use `query`, `mutation`, and `action` to register public functions. These functions are part of the public API and are exposed to the public Internet. Do NOT use `query`, `mutation`, or `action` to register sensitive internal functions that should be kept private."
                        ),
                        Guideline(
                            "You CANNOT register a function through the `api` or `internal` objects."
                        ),
                        Guideline(
                            "ALWAYS include argument and return validators for all Convex functions. If a function doesn't return anything, include `returns: v.null()` as its output validator."
                        ),
                        Guideline(
                            "If the JavaScript implementation of a Convex function doesn't have a return value, it implicitly returns `null`."
                        ),
                    ],
                ),
                GuidelineSection(
                    "function_calling",
                    [
                        Guideline(
                            "Use `ctx.runQuery` to call a query from a query, mutation, or action."
                        ),
                        Guideline(
                            "Use `ctx.runMutation` to call a mutation from a mutation or action."
                        ),
                        Guideline("Use `ctx.runAction` to call an action from an action."),
                        Guideline(
                            "ONLY call an action from another action if you need to cross runtimes (e.g. from V8 to Node). Otherwise, pull out the shared code into a helper async function and call that directly instead."
                        ),
                        Guideline(
                            "Try to use as few calls from actions to queries and mutations as possible. Queries and mutations are transactions, so splitting logic up into multiple calls introduces the risk of race conditions."
                        ),
                        Guideline(
                            "All of these calls take in a `FunctionReference`. Do NOT try to pass the callee function directly into one of these calls."
                        ),
                        Guideline(
                            """
                            When using `ctx.runQuery`, `ctx.runMutation`, or `ctx.runAction` to call a function in the same file, specify a type annotation on the return value to work around TypeScript circularity limitations. For example,
                            ```
                            export const f = query({
                              args: { name: v.string() },
                              returns: v.string(),
                              handler: async (ctx, args) => {
                                return "Hello " + args.name;
                              },
                            });

                            export const g = query({
                              args: {},
                              returns: v.null(),
                              handler: async (ctx, args) => {
                                const result: string = await ctx.runQuery(api.example.f, { name: "Bob" });
                                return null;
                              },
                            });
                            ```
                            """
                        ),
                    ],
                ),
                GuidelineSection(
                    "function_references",
                    [
                        Guideline(
                            "Function references are pointers to registered Convex functions."
                        ),
                        Guideline(
                            "Use the `api` object defined by the framework in `convex/_generated/api.ts` to call public functions registered with `query`, `mutation`, or `action`."
                        ),
                        Guideline(
                            "Use the `internal` object defined by the framework in `convex/_generated/api.ts` to call internal (or private) functions registered with `internalQuery`, `internalMutation`, or `internalAction`."
                        ),
                        Guideline(
                            "Convex uses file-based routing, so a public function defined in `convex/example.ts` named `f` has a function reference of `api.example.f`."
                        ),
                        Guideline(
                            "A private function defined in `convex/example.ts` named `g` has a function reference of `internal.example.g`."
                        ),
                        Guideline(
                            "Functions can also registered within directories nested within the `convex/` folder. For example, a public function `h` defined in `convex/messages/access.ts` has a function reference of `api.messages.access.h`."
                        ),
                    ],
                ),
                GuidelineSection(
                    "api_design",
                    [
                        Guideline(
                            "Convex uses file-based routing, so thoughtfully organize files with public query, mutation, or action functions within the `convex/` directory."
                        ),
                        Guideline(
                            "Use `query`, `mutation`, and `action` to define public functions."
                        ),
                        Guideline(
                            "Use `internalQuery`, `internalMutation`, and `internalAction` to define private, internal functions."
                        ),
                    ],
                ),
            ],
        ),
        GuidelineSection(
            "validator_guidelines",
            [
                Guideline(
                    "`v.bigint()` is deprecated for representing signed 64-bit integers. Use `v.int64()` instead."
                ),
                Guideline(
                    "Use `v.record()` for defining a record type. `v.map()` and `v.set()` are not supported."
                ),
            ],
        ),
        GuidelineSection(
            "schema_guidelines",
            [
                Guideline("Always define your schema in `convex/schema.ts`."),
                Guideline("Always import the schema definition functions from `convex/server`:"),
            ],
        ),
        GuidelineSection(
            "typescript_guidelines",
            [
                Guideline(
                    "You can use the helper typescript type 'Id' from the _generated/dataModel import to get the type of the id for a given table. For example if there is a table called 'users' you can use Id<'users'> to get the type of the id for that table."
                ),
                Guideline(
                    "If you need to define a Record make sure that you correctly provide the type of the key and value in the type. For example a validator `v.record(v.id('users'), v.string())` would have the type `Record<Id<'users'>, string>`"
                ),               
            ],
        ),
        GuidelineSection(
            "query_guidelines",
            [
                Guideline(
                    "Do NOT use `filter` in queries. Instead, define an index in the schema and use `withIndex` instead."
                ),
                Guideline(
                    "Convex queries do NOT support `.delete()`. Instead, `.collect()` the results, iterate over them, and call `ctx.db.delete(row._id)` on each result."
                ),
                GuidelineSection(
                    "ordering",
                    [
                        Guideline(
                            "By default Convex always returns documents ordered by _creationTime."
                        ), 
                        Guideline(
                            "You can use .order(`asc` | `desc`) to pick whether the order is ascending or descending. If the order isn't specified, it defaults to ascending."
                        ), 
                        Guideline(
                            "Document queries that use indexes will be ordered based on the columns in the index and can avoid slow table scans."
                        ),                  
                    ],
                ),
            ],
        ),
        GuidelineSection(
            "mutation_guidelines",
            [
                Guideline(
                    "Use `ctx.db.replace` to fully replace an existing document. This method will throw an error if the document does not exist."
                ),
                Guideline(
                    "Use `ctx.db.patch` to shallow merge updates into an existing document. This method will throw an error if the document does not exist."
                ),
            ],
        ),
        GuidelineSection(
            "scheduling_guidelines",
            [
                GuidelineSection(
                    "cron_guidelines",
                    [
                        Guideline(
                            "Only use the `crons.interval` or `crons.cron` methods to schedule cron jobs. Do NOT use the `crons.hourly`, `crons.daily`, or `crons.weekly` helpers."
                        ),
                        Guideline(
                            "Both cron methods take in a FunctionReference. Do NOT try to pass the function directly into one of these methods."
                        ),
                        Guideline(
                            """Define crons by declaring the top-level `crons` object, calling some methods on it, and then exporting it as default. For example,
                            ```ts
                            import { cronJobs } from "convex/server";
                            import { internal } from "./_generated/api";

                            const crons = cronJobs();

                            // Run `internal.users.deleteInactive` every two hours.
                            crons.interval("delete inactive users", { hours: 2 }, internal.users.deleteInactive, {});

                            export default crons;
                            ```
                            """
                        ),
                        Guideline(
                            "You can register Convex functions within `crons.ts` just like any other file."
                        ),
                        Guideline(
                            "If the function that crons calls is internal even if its in the same file you should mport the internal object from `_generated/api`."
                        ),
                    ],
                ),
            ],
        ),
        GuidelineSection(
            "file_storage_guidelines",
            [
                Guideline(
                    "Convex includes file storage for large files like images, videos, and PDFs."
                ),
                Guideline(
                    "The `ctx.storage.getUrl()` method returns a signed URL for a given file. It returns `null` if the file doesn't exist."
                ),
                Guideline(
                    """
                    Do NOT use the deprecated `ctx.storage.getMetadata` call for loading a file's metadata.

                    Instead, query the `_storage` system table. For example, you can use `ctx.db.system.get` to get an `Id<"_storage">`.
                    ```
                    import { query } from "./_generated/server";
                    import { Id } from "./_generated/dataModel";

                    type FileMetadata = {
                        _id: Id<"_storage">;
                        _creationTime: number;
                        contentType?: string;
                        sha256: string;
                        size: number;
                    }

                    export const exampleQuery = query({
                        args: { fileId: v.id("_storage") },
                        returns: v.null();
                        handler: async (ctx, args) => {
                            const metadata: FileMetadata | null = await ctx.db.system.get(args.fileId);
                            console.log(metadata);
                            return null;
                        },
                    });
                    ```
                    """
                ),
            ],
        ),
    ],
)
