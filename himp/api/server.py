"""
HIMP REST API Server.
"""

from contextlib import asynccontextmanager

import logging
import subprocess
import time

from fastapi import Depends, FastAPI
from fastapi.encoders import jsonable_encoder
from fastapi.requests import Request
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from himp.lib.logging_config import configure_logging

configure_logging()

logger = logging.getLogger("himp")

@asynccontextmanager
async def application_lifespan(_app):
    try:
        yield
    finally:
        PostgreSQLDatabase.close_pools()


from himp.api.auth import router as auth_router
from himp.api.dependencies import require_admin, require_page_admin, require_page_session, require_session
from himp.api.dashboard import router as dashboard_router
from himp.api.discovery import router as discovery_router
from himp.api.execution import router as execution_router
from himp.api.inventory import router as inventory_router
from himp.api.update import router as update_router
from himp.api.users import router as users_router
from himp.api.health import router as health_router
from himp.api.host_health import router as host_health_router
from himp.api.health_history import router as health_history_router
from himp.api.health_trends import router as health_trends_router
from himp.api.automation import router as automation_router
from himp.api.scheduler import router as scheduler_router
from himp.api.workflows import (
    router as workflows_router,
    workflow_execution_service,
)
from himp.api.remediation import (
    router as remediation_router,
)
from himp.api.relationships import router as relationships_router
from himp.api.dependency_impact import router as dependency_impact_router
from himp.api.health_analysis import router as health_analysis_router
from himp.database.postgresql import PostgreSQLDatabase
from himp.database.remediation_audit import (
    RemediationAuditRepository,
)
from himp.services.scheduler import SchedulerService
from himp.services.logs import LogService
from himp.app import HIMP


app = FastAPI(
    title="Homelab Infrastructure Management Platform",
    version="1.0.1",
    lifespan=application_lifespan,
)


async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
):
    logger.exception(
        "Unhandled HIMP API exception: %s",
        exc,
    )

    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error"
        },
    )


app.add_exception_handler(
    Exception,
    unhandled_exception_handler,
)

app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static",
)

app.include_router(
    auth_router,
    prefix="/api",
)

app.include_router(
    dashboard_router,
    prefix="/api",
    dependencies=[Depends(require_session)],
)

app.include_router(
    execution_router,
    prefix="/api",
    dependencies=[Depends(require_session)],
)

app.include_router(
    inventory_router,
    prefix="/api",
    dependencies=[Depends(require_session)],
)

app.include_router(
    update_router,
    prefix="/api",
    dependencies=[Depends(require_session)],
)

app.include_router(
    users_router,
    prefix="/api",
    dependencies=[Depends(require_admin)],
)

app.include_router(
    discovery_router,
    prefix="/api",
    dependencies=[Depends(require_session)],
)

app.include_router(
    host_health_router,
    prefix="/api",
    dependencies=[Depends(require_session)],
)

app.include_router(
    health_router,
    prefix="/api",
    dependencies=[Depends(require_session)],
)

app.include_router(
    health_history_router,
    prefix="/api",
    dependencies=[Depends(require_session)],
)

app.include_router(
    health_trends_router,
    prefix="/api",
    dependencies=[Depends(require_session)],
)

app.include_router(
    automation_router,
    prefix="/api",
    dependencies=[Depends(require_session)],
)

app.include_router(
    scheduler_router,
    prefix="/api",
    dependencies=[Depends(require_session)],
)

app.include_router(
    workflows_router,
    prefix="/api",
    dependencies=[Depends(require_session)],
)

app.include_router(
    remediation_router,
    prefix="/api",
    dependencies=[Depends(require_session)],
)

app.include_router(
    relationships_router,
    prefix="/api",
    dependencies=[Depends(require_session)],
)

app.include_router(
    dependency_impact_router,
    prefix="/api",
    dependencies=[Depends(require_session)],
)

app.include_router(
    health_analysis_router,
    prefix="/api",
    dependencies=[Depends(require_session)],
)

templates = Jinja2Templates(
    directory="templates"
)

himp = HIMP()

remediation_audit_repository = (
    RemediationAuditRepository()
)

log_service = LogService()

workflow_execution_service.automation_service = (
    himp.automation
)


@app.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={},
    )


@app.get("/system/status")
def himp_status(
    _session=Depends(require_session),
):

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
def restart_himp(
    _session=Depends(require_admin),
):

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


@app.get("/", dependencies=[Depends(require_page_session)])
def home(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context=dashboard_context(),
    )


@app.get("/inventory", dependencies=[Depends(require_page_session)])
def inventory(request: Request):

    context = dashboard_context()

    context["inventory"] = himp.inventory.summary()

    context["storage_summary"] = (
        himp.storage.summary()
    )

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


@app.get("/inventory/hosts/{hostname}", dependencies=[Depends(require_page_session)])
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

        context["storage"] = (
            himp.storage.host(
                hostname
            )
        )

    else:

        context["changes"] = []
        context["current_health"] = None
        context["health_history"] = []
        context["storage"] = None

    return templates.TemplateResponse(
        request=request,
        name="inventory_host.html",
        context=context,
    )


@app.get("/discovery", dependencies=[Depends(require_page_session)])
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



@app.get("/health", dependencies=[Depends(require_page_session)])
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


@app.get("/reports", dependencies=[Depends(require_page_session)])
def reports(request: Request):

    context = dashboard_context()

    context["reports"] = (
        himp.reports.summary()
    )

    context["operational_summary"] = (
        himp.reports.operational_summary()
    )

    context["report_files"] = (
        himp.reports.files()
    )

    return templates.TemplateResponse(
        request=request,
        name="reports.html",
        context=context,
    )


@app.get(
    "/application-health",
    dependencies=[Depends(require_page_session)],
)
def application_health(request: Request):

    context = dashboard_context()

    context["application_health"] = (
        himp.application_health.summary()
    )

    return templates.TemplateResponse(
        request=request,
        name="application_health.html",
        context=context,
    )


@app.get("/settings", dependencies=[Depends(require_page_session)])
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


@app.get("/automation", dependencies=[Depends(require_page_session)])
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


@app.get("/plugins", dependencies=[Depends(require_page_session)])
def plugins(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="plugins.html",
        context=dashboard_context(),
    )


@app.get("/automation/executions/{execution_id}", dependencies=[Depends(require_page_session)])
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


@app.get("/plugins/{plugin_id}", dependencies=[Depends(require_page_session)])
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


@app.get("/history", dependencies=[Depends(require_page_session)])
def history(request: Request):

    context = dashboard_context()

    context["history"] = jsonable_encoder(
        log_service.history(100)
    )

    return templates.TemplateResponse(
        request=request,
        name="history.html",
        context=context,
    )


@app.get("/api/logs", dependencies=[Depends(require_session)])
def logs_api(limit: int = 100):
    limit = max(1, min(limit, 500))

    return JSONResponse(
        {
            "logs": jsonable_encoder(
                log_service.history(limit)
            ),
            "limit": limit,
        }
    )


@app.get("/api/logs/export/json", dependencies=[Depends(require_session)])
def logs_export_json():
    import json
    from fastapi.responses import Response

    content = json.dumps(
        log_service.history(500),
        indent=2,
        default=str,
    )

    return Response(
        content=content,
        media_type="application/json",
        headers={
            "Content-Disposition": (
                'attachment; filename="himp-operational-logs.json"'
            ),
        },
    )


@app.get("/api/logs/export/txt", dependencies=[Depends(require_session)])
def logs_export_txt():
    from fastapi.responses import Response

    records = log_service.history(500)

    lines = []

    for record in records:
        lines.extend(
            [
                f"Timestamp: {record['timestamp']}",
                f"Source: {record['source']}",
                f"Event: {record['event']}",
                f"Status: {record['status']}",
                f"Message: {record['message']}",
                f"ID: {record['id']}",
                f"Details: {record['details']}",
                "",
            ]
        )

    content = "\n".join(lines)

    return Response(
        content=content,
        media_type="text/plain; charset=utf-8",
        headers={
            "Content-Disposition": (
                'attachment; filename="himp-operational-logs.txt"'
            ),
        },
    )


@app.get("/api/logs/export/csv", dependencies=[Depends(require_session)])
def logs_export_csv():
    import csv
    import io
    import json
    from fastapi.responses import Response

    max_cell_length = 32767

    def csv_cell(value):
        if isinstance(value, (dict, list, tuple)):
            value = json.dumps(
                value,
                default=str,
                ensure_ascii=False,
            )
        else:
            value = str(value)

        if len(value) <= max_cell_length:
            return value

        return (
            value[: max_cell_length - len(" [truncated]")]
            + " [truncated]"
        )

    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer)

    writer.writerow(
        [
            "id",
            "timestamp",
            "source",
            "event",
            "status",
            "message",
            "details",
        ]
    )

    for record in log_service.history(500):
        writer.writerow(
            [
                csv_cell(record["id"]),
                csv_cell(record["timestamp"]),
                csv_cell(record["source"]),
                csv_cell(record["event"]),
                csv_cell(record["status"]),
                csv_cell(record["message"]),
                csv_cell(record["details"]),
            ]
        )

    return Response(
        content=buffer.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": (
                'attachment; filename="himp-operational-logs.csv"'
            ),
        },
    )


@app.get("/remediation", dependencies=[Depends(require_page_session)])
def remediation(
    request: Request,
    source_type: str | None = None,
    source_id: str | None = None,
    decision: str | None = None,
    audit_id: int | None = None,
):

    context = dashboard_context()

    context["remediation"] = (
        remediation_audit_repository.history(
            limit=50,
            source_type=source_type,
            source_id=source_id,
            decision=decision,
        )
    )

    context["source_type"] = source_type
    context["source_id"] = source_id
    context["decision"] = decision
    context["remediation_detail_id"] = audit_id
    context["remediation_detail"] = (
        remediation_audit_repository.find(audit_id)
        if audit_id is not None
        else None
    )
    context["remediation_summary"] = (
        remediation_audit_repository.summary()
    )

    return templates.TemplateResponse(
        request=request,
        name="remediation.html",
        context=context,
    )


@app.get(
    "/api/application-health",
    dependencies=[Depends(require_session)],
)
def application_health_api():

    return JSONResponse(
        himp.application_health.summary()
    )


@app.get("/api/reports/host/{hostname}/pdf", dependencies=[Depends(require_session)])
def host_report_pdf_api(hostname: str):

    from fastapi.responses import Response
    from himp.services.host_report_export import (
        HostReportExportService,
    )

    pdf = HostReportExportService().pdf(hostname)

    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{hostname}-report.pdf"'
            ),
        },
    )


@app.get("/api/reports/host/{hostname}/txt", dependencies=[Depends(require_session)])
def host_report_txt_api(hostname: str):

    from fastapi.responses import Response
    from himp.services.host_report_export import (
        HostReportExportService,
    )

    content = HostReportExportService().txt(hostname)

    return Response(
        content=content,
        media_type="text/plain; charset=utf-8",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{hostname}-report.txt"'
            ),
        },
    )


@app.get("/api/reports/host/{hostname}/csv", dependencies=[Depends(require_session)])
def host_report_csv_api(hostname: str):

    from fastapi.responses import Response
    from himp.services.host_report_export import (
        HostReportExportService,
    )

    content = HostReportExportService().csv(hostname)

    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{hostname}-report.csv"'
            ),
        },
    )


@app.get("/api/reports/pdf", dependencies=[Depends(require_session)])
def reports_pdf_api():

    from himp.services.report_pdf import ReportPDFService

    pdf = ReportPDFService().generate(
        himp.reports.operational_summary()
    )

    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                'attachment; filename="himp-operational-report.pdf"'
            ),
        },
    )


@app.get("/api/reports", dependencies=[Depends(require_session)])
def reports_api():

    return JSONResponse(
        {
            "summary": himp.reports.summary(),
            "operational_summary": (
                himp.reports.operational_summary()
            ),
            "files": himp.reports.files(),
        }
    )


@app.get("/api/settings", dependencies=[Depends(require_session)])
def settings_api():

    return JSONResponse(
        himp.settings.summary()
    )


@app.get("/api/automation", dependencies=[Depends(require_session)])
def automation_api():

    return JSONResponse(
        himp.automation.summary()
    )


@app.get("/api", dependencies=[Depends(require_session)])
def api_root():

    return JSONResponse(
        {
            "application": "HIMP",
            "status": "running",
            "version": "1.0.0",
        }
    )


@app.get(
    "/users",
    dependencies=[Depends(require_page_admin)],
)
def users_page(
    request: Request,
    _session=Depends(require_page_admin),
):
    from himp.api.users import user_management

    context = dashboard_context()
    context["users"] = user_management.list_users()
    context["current_user"] = {
        "username": _session.username,
        "role": _session.role,
    }

    return templates.TemplateResponse(
        request=request,
        name="users.html",
        context=context,
    )
