from fastapi import APIRouter

router = APIRouter()

@router.get("/hello")
def say_hello(name: str = "World"):
    return {"message": f"Hello, {name}!"}
