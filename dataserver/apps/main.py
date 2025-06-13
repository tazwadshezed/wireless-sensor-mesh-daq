import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv

load_dotenv()  # Pulls in values from .env

# Import all routers
from apps.routes import router as main_router

# Initialize FastAPI app
app = FastAPI(
    title="Data Server API",
    description="Backend API for mesh dashboard and visualization",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Mount static files
app.mount("/daq-demo/static", StaticFiles(directory="apps/static"), name="daq-static")



# Include main router
app.include_router(main_router, prefix="/daq-demo")

# Health check root
@app.get("/", tags=["System"])
async def root():
    return {"message": "Data Server is running!"}


# Entrypoint to run directly
if __name__ == "__main__":
     uvicorn.run(
        "dataserver.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        proxy_headers=True
    )
