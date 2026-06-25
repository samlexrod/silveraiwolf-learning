import "dotenv/config";
import express from "express";
import { createServer } from "node:http";
import cors from "cors";
import { ApolloServer } from "@apollo/server";
import { expressMiddleware } from "@apollo/server/express4";
import { makeExecutableSchema } from "@graphql-tools/schema";
import { WebSocketServer } from "ws";
import { useServer } from "graphql-ws/lib/use/ws";
import { typeDefs, resolvers } from "./schema.js";
import { chatHandler, authStatusHandler, loginHandler } from "./chat.js";

const schema = makeExecutableSchema({ typeDefs, resolvers });

const app = express();
const httpServer = createServer(app);

// WebSocket server for GraphQL subscriptions (same /graphql path).
const wsServer = new WebSocketServer({ server: httpServer, path: "/graphql" });
const serverCleanup = useServer({ schema }, wsServer);

const apollo = new ApolloServer({
  schema,
  plugins: [
    {
      async serverWillStart() {
        return {
          async drainServer() {
            await serverCleanup.dispose();
          },
        };
      },
    },
  ],
});

await apollo.start();
app.use("/graphql", cors<cors.CorsRequest>(), express.json(), expressMiddleware(apollo));

// Claude assistant — streams via SSE using the learner's own Anthropic key (held in memory only),
// or the machine's ambient credentials if no key is supplied.
app.options("/api/chat", cors<cors.CorsRequest>()); // CORS preflight for the JSON+header POST
app.options("/api/chat/login", cors<cors.CorsRequest>());
app.get("/api/chat/auth-status", cors<cors.CorsRequest>(), authStatusHandler);
app.post("/api/chat/login", cors<cors.CorsRequest>(), loginHandler);
app.post("/api/chat", cors<cors.CorsRequest>(), express.json({ limit: "1mb" }), chatHandler);

const PORT = Number(process.env.PORT ?? 4000);
httpServer.listen(PORT, () => {
  console.log(`🚀 GraphQL  http://localhost:${PORT}/graphql`);
  console.log(`🔌 Subscriptions  ws://localhost:${PORT}/graphql`);
});
