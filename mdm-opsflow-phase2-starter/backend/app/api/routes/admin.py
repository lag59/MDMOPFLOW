from fastapi import APIRouter
router=APIRouter(prefix="/api/admin",tags=["Platform Administration"])
@router.get("/overview")
async def overview():
    return {"platform":"MDM OpsFlow","status":"foundation-ready","role":"platform_super_admin"}
