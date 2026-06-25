import { PubSub } from "graphql-subscriptions";

// In-process bus that bridges Postgres LISTEN/NOTIFY events (published by session.ts)
// to GraphQL subscriptions.
export const pubsub = new PubSub();
export const ROW_CHANGED = "ROW_CHANGED";
