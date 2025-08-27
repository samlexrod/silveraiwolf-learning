import strawberry

@strawberry.type
class Query:
    @strawberry.field
    async def health_check(self) -> str:
        return "API is running"
