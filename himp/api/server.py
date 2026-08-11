"""
HIMP REST API Server.
"""

import subprocess
import time

from fastapi import FastAPI
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from himp.api.dashboard import router as dashboard_router
from himp.api.discovery import router as discovery_router
from himp.api.execution import router as execution_router
from himp.api.inventory import router as inventory_router
from himp.api.update import router as update_router
from himp.api.health import router as health_router
from himp.api.host_health import router as host_health_router
from himp.api.health_history import router as health_history_router
from himp.api.health_trends import router as health_trends_router
from himp.api.automation import router as automation_router
from himp.api.scheduler import router as scheduler_router
from himp.services.scheduler import SchedulerService
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
    update_router,
    prefix="/api",
)

app.include_router(
    discovery_router,
    prefix="/api",
)

app.include_router(
    host_health_router,
    prefix="/api",
)

app.include_router(
    health_router,
    prefix="/api",
)

app.include_router(
    health_history_router,
    prefix="/api",
)

app.include_router(
    health_trends_router,
    prefix="/api",
)

app.include_router(
    automation_router,
    prefix="/api",
)

app.include_router(
    scheduler_router,
    prefix="/api",
)

templates = Jinja2Templates(
    directory="templates"
)

himp = HIMP()


@app.get("/system/status")
def himp_status():

    status = subprocess.run(
        [
            "systemctl",
            "is-active",
            "himp",
        ],
        capture_output=True,
        text=True,
    )

    pid = subprocess.run(
        [
            "systemctl",
            "show",
            "himp",
            "--property=MainPID",
            "--value",
        ],
        capture_output=True,
        text=True,
    )

    started = subprocess.run(
        [
            "systemctl",
            "show",
            "himp",
            "--property=ActiveEnterTimestamp",
            "--value",
        ],
        capture_output=True,
        text=True,
    )

    return {
        "service": "himp",
        "status": status.stdout.strip(),
        "running": status.returncode == 0,
        "pid": pid.stdout.strip(),
        "started": started.stdout.strip(),
    }


@app.post("/system/restart")
def restart_himp():

    subprocess.Popen(
        [
            "bash",
            "-c",
            "sleep 1 && systemctl restart himp",
        ],
        start_new_session=True,
    )

    return {
        "status": "restart_requested"
    }



def dashboard_context():

    status = subprocess.run(
        [
            "systemctl",
            "is-active",
            "himp",
        ],
        capture_output=True,
        text=True,
    )

    pid = subprocess.run(
        [
            "systemctl",
            "show",
            "himp",
            "--property=MainPID",
            "--value",
        ],
        capture_output=True,
        text=True,
    )

    started = subprocess.run(
        [
            "systemctl",
            "show",
            "himp",
            "--property=ActiveEnterTimestamp",
            "--value",
        ],
        capture_output=True,
        text=True,
    )

    return {
        "dashboard": himp.dashboard.summary(),
        "system": {
            "service": "himp",
            "status": status.stdout.strip(),
            "running": status.returncode == 0,
            "pid": pid.stdout.strip(),
            "started": started.stdout.strip(),
        },
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

    context["inactive_hosts"] = [
        dict(host)
        for host in himp.inventory.repository.all_hosts(
            include_inactive=True
        )
        if not host["active"]
    ]

    return templates.TemplateResponse(
        request=request,
        name="inventory.html",
        context=context,
    )


@app.get("/inventory/hosts/{hostname}")
def inventory_host(
    request: Request,
    hostname: str,
):

    host = himp.inventory.find_host(
        hostname
    )

    context = dashboard_context()

    context["host"] = host

    if host:

        context["changes"] = [
            dict(change)
            for change in himp.inventory.changes()
            if change["hostname"] == hostname
        ]

        context["current_health"] = (
            himp.dashboard.host_health.current(
                hostname,
            )
        )

        context["health_history"] = (
            himp.dashboard.host_health.history(
                hostname=hostname,
                limit=50,
            )
        )

    else:

        context["changes"] = []
        context["current_health"] = None
        context["health_history"] = []

    return templates.TemplateResponse(
        request=request,
        name="inventory_host.html",
        context=context,
    )


@app.get("/discovery")
def discovery(request: Request):

    records = [
        dict(record)
        for record in himp.discovery.all()
    ]

    context = dashboard_context()

    context["discovery"] = {
        "count": himp.discovery.count(),
        "records": records,
    }

    return templates.TemplateResponse(
        request=request,
        name="discovery.html",
        context=context,
    )



@app.get("/health")
def health(request: Request):

    context = dashboard_context()

    context["health"] = himp.health.summary()

    context["health_trends"] = (
        himp.health_trends.summary()
    )

    return templates.TemplateResponse(
        request=request,
        name="health.html",
        context=context,
    )


@app.get("/reports")
def reports(request: Request):

    context = dashboard_context()

    context["reports"] = (
        himp.reports.summary()
    )

    context["report_files"] = (
        himp.reports.files()
    )

    return templates.TemplateResponse(
        request=request,
        name="reports.html",
        context=context,
    )


@app.get("/settings")
def settings(request: Request):

    context = dashboard_context()

    context["settings"] = (
        himp.settings.summary()
    )

    return templates.TemplateResponse(
        request=request,
        name="settings.html",
        context=context,
    )


@app.get("/automation")
def automation(
    request: Request,
    task_id: str | None = None,
    success: bool | None = None,
):

    context = dashboard_context()

    context["automation"] = (
        himp.automation.summary()
    )

    scheduler = SchedulerService()
    schedules = scheduler.all()

    schedules = [
        {
            **dict(schedule),
            "next_run": (
                next_run.isoformat()
                if (next_run := scheduler.next_run(schedule))
                is not None
                else None
            ),
            "execution_status": scheduler.execution_status(
                schedule["task_id"]
            ),
        }
        for schedule in schedules
    ]

    context["schedules"] = schedules
    context["schedule_map"] = {
        schedule["task_id"]: schedule
        for schedule in schedules
    }

    context["automation_executions"] = (
        himp.automation.execution_repository.history(
            limit=10,
            task_id=task_id,
            success=success,
        )
    )

    context["automation_task_filter"] = task_id
    context["automation_success_filter"] = success
    context["automation_execution_count"] = len(
        context["automation_executions"]
    )

    return templates.TemplateResponse(
        request=request,
        name="automation.html",
        context=context,
    )


@app.get("/plugins")
def plugins(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="plugins.html",
        context=dashboard_context(),
    )


@app.get("/automation/executions/{execution_id}")
def automation_execution_details(
    request: Request,
    execution_id: int,
):

    execution = (
        himp.automation.execution_repository.find(
            execution_id
        )
    )

    context = dashboard_context()
    context["execution"] = execution

    return templates.TemplateResponse(
        request=request,
        name="automation_execution_details.html",
        context=context,
    )


@app.get("/plugins/{plugin_id}")
def plugin_details(
    request: Request,
    plugin_id: str,
):

    details = himp.plugins.details(plugin_id)

    context = dashboard_context()

    context["details"] = details

    if details is not None:
        context["plugin"] = details["plugin"]
        context["validation"] = details["validation"]
        context["health"] = details["health"]
        context["executions"] = details["executions"]
        context["discovery"] = details["discovery"]

    return templates.TemplateResponse(
        request=request,
        name="plugin_details.html",
        context=context,
    )


@app.get("/history")
def history(request: Request):

    context = dashboard_context()

    context["history"] = (
        himp.execution.history(50)
    )

    return templates.TemplateResponse(
        request=request,
        name="history.html",
        context=context,
    )


@app.get("/api/reports")
def reports_api():

    return JSONResponse(
        {
            "summary": himp.reports.summary(),
            "files": himp.reports.files(),
        }
    )


@app.get("/api/settings")
def settings_api():

    return JSONResponse(
        himp.settings.summary()
    )


@app.get("/api/automation")
def automation_api():

    return JSONResponse(
        himp.automation.summary()
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
