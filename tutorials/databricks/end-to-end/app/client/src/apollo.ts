import { ApolloClient, InMemoryCache, HttpLink, split } from "@apollo/client";
import { GraphQLWsLink } from "@apollo/client/link/subscriptions";
import { getMainDefinition } from "@apollo/client/utilities";
import { createClient } from "graphql-ws";

const SERVER = import.meta.env.VITE_SERVER ?? "localhost:4000";

const httpLink = new HttpLink({ uri: `http://${SERVER}/graphql` });

const wsLink = new GraphQLWsLink(
  createClient({ url: `ws://${SERVER}/graphql` }),
);

// Route subscriptions over WebSocket, everything else over HTTP.
const link = split(
  ({ query }) => {
    const def = getMainDefinition(query);
    return def.kind === "OperationDefinition" && def.operation === "subscription";
  },
  wsLink,
  httpLink,
);

export const client = new ApolloClient({
  link,
  cache: new InMemoryCache(),
});
