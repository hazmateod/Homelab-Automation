"""
HIMP REST API Server.
"""

from fastapi import FastAPI
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from himp.api.dashboard import router as dashboard_router
from himp.api.discovery import router as discovery_router
from himp.api.execution import router as execution_router
from himp.api.inventory import router as inventory_router
from himp.app import HIMP


app = FastAPI(
    title="Homelab Infrastructure Management Platform",
    version="1.0.0",
)

app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static",
)

app.include_router(
    dashboard_router,
    prefix="/api",
)

app.include_router(
    execution_router,
    prefix="/api",
)

app.include_router(
    inventory_router,
    prefix="/api",
)

app.include_router(
    discovery_router,
    prefix="/api",
)

templates = Jinja2Templates(
    directory="templates"
)

himp = HIMP()


def dashboard_context():

    return {
        "dashboard": himp.dashboard.summary(),
    }


@app.get("/")
def home(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context=dashboard_context(),
    )


@app.get("/inventory")
def inventory(request: Request):

    context = dashboard_context()

    context["inventory"] = himp.inventory.summary()

    return templates.TemplateResponse(
        request=request,
        name="inventory.html",
        context=context,
    )


@app.get("/plugins")
def plugins(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="plugins.html",
        context=dashboard_context(),
    )


@app.get("/plugins/{plugin_id}")
def plugin_details(
    request: Request,
    plugin_id: str,
):

    plugin = himp.plugins.find(plugin_id)

    context = dashboard_context()

    context["plugin"] = plugin

    context["executions"] = [
        execution
        for execution in himp.execution.history(50)
        if execution["plugin"] == plugin_id
    ]

    context["validation"] = himp.validation.validate(plugin_id)

    return templates.TemplateResponse(
        request=request,
        name="plugin_details.html",
        context=context,
    )


@app.get("/history")
def history(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="history.html",
        context=dashboard_context(),
    )


@app.get("/api")
def api_root():

    return JSONResponse(
        {
            "application": "HIMP",
            "status": "running",
            "version": "1.0.0",
        }
    )
