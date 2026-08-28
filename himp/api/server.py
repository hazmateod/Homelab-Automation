"""
HIMP REST API Server.
"""

from contextlib import asynccontextmanager

import logging
import subprocess
import time

from fastapi import Depends, FastAPI, HTTPException
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
from himp.api.maintenance_windows import router as maintenance_windows_router
from himp.api.workflows import (
    router as workflows_router,
    workflow_execution_service,
)
from himp.api.remediation import (
    remediation_approval_service,
    remediation_scheduling_service,
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
from himp.services.maintenance_windows import MaintenanceWindowService
from himp.services.logs import LogService
from himp.services.vulnerability_intelligence import (
    VulnerabilityIntelligenceService,
)
from himp.services.vulnerability_rescan import (
    VulnerabilityRescanService,
)
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
    maintenance_windows_router,
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

vulnerability_intelligence_service = (
    VulnerabilityIntelligenceService()
)

vulnerability_rescan_service = (
    VulnerabilityRescanService(
        inventory=himp.inventory,
    )
)

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


@app.get("/inventory")
def inventory(
    request: Request,
    session=Depends(require_page_session),
):

    context = dashboard_context()

    context["inventory"] = himp.inventory.summary()

    context["vulnerability_scan_admin"] = (
        session.role == "admin"
    )

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


@app.get(
    "/vulnerabilities",
    dependencies=[Depends(require_page_session)],
)
def vulnerabilities(request: Request):

    context = dashboard_context()

    context["vulnerability"] = (
        vulnerability_intelligence_service
        .overview()
    )

    return templates.TemplateResponse(
        request=request,
        name="vulnerabilities.html",
        context=context,
    )


@app.post(
    "/api/vulnerabilities/hosts/{hostname}/rescan",
)
def vulnerability_host_rescan_api(
    hostname: str,
    _admin=Depends(require_admin),
):
    try:
        return (
            vulnerability_rescan_service
            .start(
                hostname,
                timeout=60,
            )
        )

    except LookupError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except RuntimeError as exc:
        raise HTTPException(
            status_code=502,
            detail=(
                "Greenbone rescan request failed: "
                f"{exc}"
            ),
        ) from exc


@app.get(
    "/vulnerabilities/hosts/{hostname}",
)
def vulnerability_host(
    request: Request,
    hostname: str,
    session=Depends(require_page_session),
):

    host = himp.inventory.find_host(
        hostname
    )

    if host is None:
        raise HTTPException(
            status_code=404,
            detail="Inventory host not found",
        )

    context = dashboard_context()

    context["vulnerability_host"] = (
        vulnerability_intelligence_service
        .host_detail(
            hostname
        )
    )

    from himp.services.vulnerability_comparison import (
        VulnerabilityComparisonService,
    )

    context["vulnerability_comparison"] = (
        VulnerabilityComparisonService()
        .compare_host(
            hostname,
            limit=3,
        )
    )

    context["inventory_host"] = host

    context["vulnerability_rescan_admin"] = (
        session.role == "admin"
    )

    return templates.TemplateResponse(
        request=request,
        name="vulnerability_host.html",
        context=context,
    )


@app.get(
    "/api/vulnerabilities/hosts/{hostname}/pdf",
    dependencies=[Depends(require_session)],
)
def vulnerability_host_pdf_api(
    hostname: str,
):
    from fastapi.responses import Response
    from himp.services.vulnerability_report_export import (
        VulnerabilityReportExportService,
    )

    content = (
        VulnerabilityReportExportService()
        .pdf(
            hostname
        )
    )

    return Response(
        content=content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                "attachment; "
                f'filename="{hostname}-vulnerabilities.pdf"'
            ),
        },
    )


@app.get(
    "/api/vulnerabilities/hosts/{hostname}/txt",
    dependencies=[Depends(require_session)],
)
def vulnerability_host_txt_api(
    hostname: str,
):
    from fastapi.responses import Response
    from himp.services.vulnerability_report_export import (
        VulnerabilityReportExportService,
    )

    content = (
        VulnerabilityReportExportService()
        .txt(
            hostname
        )
    )

    return Response(
        content=content,
        media_type="text/plain; charset=utf-8",
        headers={
            "Content-Disposition": (
                "attachment; "
                f'filename="{hostname}-vulnerabilities.txt"'
            ),
        },
    )


@app.get(
    "/api/vulnerabilities/hosts/{hostname}/csv",
    dependencies=[Depends(require_session)],
)
def vulnerability_host_csv_api(
    hostname: str,
):
    from fastapi.responses import Response
    from himp.services.vulnerability_report_export import (
        VulnerabilityReportExportService,
    )

    content = (
        VulnerabilityReportExportService()
        .csv(
            hostname
        )
    )

    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": (
                "attachment; "
                f'filename="{hostname}-vulnerabilities.csv"'
            ),
        },
    )


@app.get(
    "/vulnerabilities/reports/{report_id}",
    dependencies=[Depends(require_page_session)],
)
def vulnerability_report(
    request: Request,
    report_id: str,
):

    detail = (
        vulnerability_intelligence_service
        .report_detail(
            report_id
        )
    )

    if detail is None:
        raise HTTPException(
            status_code=404,
            detail="Vulnerability report not found",
        )

    context = dashboard_context()

    context["vulnerability_report"] = (
        detail
    )

    return templates.TemplateResponse(
        request=request,
        name="vulnerability_report.html",
        context=context,
    )


@app.get(
    "/vulnerabilities/findings/{result_id}",
    dependencies=[Depends(require_page_session)],
)
def vulnerability_finding(
    request: Request,
    result_id: str,
):

    detail = (
        vulnerability_intelligence_service
        .finding_detail(
            result_id
        )
    )

    if detail is None:
        raise HTTPException(
            status_code=404,
            detail="Vulnerability finding not found",
        )

    context = dashboard_context()

    context["vulnerability_finding"] = (
        detail
    )

    return templates.TemplateResponse(
        request=request,
        name="vulnerability_finding.html",
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

    context["operational_attention"] = (
        himp.dashboard.operational_summary()
    )

    for item in context["operational_attention"]["attention"]:
        item["guidance"] = (
            himp.operator_guidance.safe_for_attention(
                item
            )
        )

    return templates.TemplateResponse(
        request=request,
        name="application_health.html",
        context=context,
    )


@app.get("/notifications")
def notifications(
    request: Request,
    lifecycle_status: str | None = None,
    severity: str | None = None,
    session=Depends(require_page_session),
):
    if (
        lifecycle_status is not None
        and lifecycle_status
        not in himp.notifications.repository.LIFECYCLE_STATUSES
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid notification lifecycle status",
        )

    if (
        severity is not None
        and severity
        not in himp.notifications.repository.SEVERITIES
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid notification severity",
        )

    context = dashboard_context()

    context["notification_summary"] = (
        himp.notifications.summary(
            limit=100,
            lifecycle_status=lifecycle_status,
            severity=severity,
        )
    )

    context["notification_filters"] = {
        "lifecycle_status": lifecycle_status,
        "severity": severity,
    }

    context["notification_lifecycle_statuses"] = (
        sorted(
            himp.notifications.repository
            .LIFECYCLE_STATUSES
        )
    )

    context["notification_severities"] = (
        sorted(
            himp.notifications.repository
            .SEVERITIES
        )
    )

    context["can_acknowledge_notifications"] = (
        session.role == "admin"
    )

    return templates.TemplateResponse(
        request=request,
        name="notifications.html",
        context=context,
    )


@app.post(
    "/api/notifications/{notification_id}/acknowledge"
)
def acknowledge_notification(
    notification_id: int,
    admin=Depends(require_admin),
):
    try:
        return himp.notifications.acknowledge(
            notification_id,
            admin.username,
        )

    except KeyError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        ) from error

    except ValueError as error:
        raise HTTPException(
            status_code=409,
            detail=str(error),
        ) from error


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

    maintenance_windows = MaintenanceWindowService()

    context["maintenance_windows"] = (
        maintenance_windows.list(
            limit=100,
        )["windows"]
    )

    context["active_maintenance_windows"] = (
        maintenance_windows.active_all()
    )

    context["upcoming_maintenance_windows"] = (
        maintenance_windows.upcoming(
            limit=25,
        )
    )

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

    workflow_navigation = {
        "origin_workflow_id": None,
        "origin_workflow_execution_id": None,
        "retry_source_workflow_id": None,
        "retry_source_workflow_execution_id": None,
        "retry_of_execution_id": None,
    }

    if execution is not None:
        from himp.api.workflows import workflow_history_service

        origin_execution_id = execution.get(
            "workflow_execution_id"
        )
        retry_source_execution_id = execution.get(
            "retry_source_workflow_execution_id"
        )

        if origin_execution_id:
            origin_run = (
                workflow_history_service
                .workflow_execution_repository
                .find(origin_execution_id)
            )

            if origin_run is not None:
                workflow_navigation[
                    "origin_workflow_id"
                ] = origin_run.get("workflow_id")
                workflow_navigation[
                    "origin_workflow_execution_id"
                ] = origin_execution_id

        if retry_source_execution_id:
            retry_source_run = (
                workflow_history_service
                .workflow_execution_repository
                .find(retry_source_execution_id)
            )

            if retry_source_run is not None:
                workflow_navigation[
                    "retry_source_workflow_id"
                ] = retry_source_run.get("workflow_id")
                workflow_navigation[
                    "retry_source_workflow_execution_id"
                ] = retry_source_execution_id

        workflow_navigation[
            "retry_of_execution_id"
        ] = execution.get(
            "retry_of_execution_id"
        )

    context["workflow_navigation"] = workflow_navigation

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


@app.get(
    "/workflows",
    dependencies=[Depends(require_page_session)],
)
def workflows_page(
    request: Request,
):
    """
    Render the operator workflow landing page using the existing
    workflow and workflow-history services.
    """
    from himp.api.workflows import (
        workflow_history_service,
        workflow_service,
    )

    workflow_rows = []

    for workflow in workflow_service.list_workflows():
        history = workflow_history_service.history(
            workflow["id"],
            limit=1,
        )

        latest = (
            history[0]
            if history
            else None
        )

        workflow_rows.append(
            {
                **workflow,
                "latest": latest,
            }
        )

    context = dashboard_context()
    context["workflow_rows"] = workflow_rows

    return templates.TemplateResponse(
        request=request,
        name="workflows.html",
        context=context,
    )


@app.get(
    "/workflows/{workflow_id}/history",
    dependencies=[Depends(require_page_session)],
)
def workflow_history_page(
    request: Request,
    workflow_id: int,
):
    """
    Render persisted execution history for one workflow.

    WorkflowHistoryService remains authoritative. This page creates
    navigation only and does not persist a second history model.
    """
    from himp.api.workflows import workflow_history_service

    try:
        workflow_runs = workflow_history_service.history(
            workflow_id,
            limit=100,
        )
        workflow = (
            workflow_history_service.workflow_service.get_workflow(
                workflow_id
            )
        )
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail="Workflow not found",
        )

    context = dashboard_context()
    context["workflow"] = workflow
    context["workflow_runs"] = workflow_runs

    return templates.TemplateResponse(
        request=request,
        name="workflow_history.html",
        context=context,
    )


@app.get(
    "/workflows/{workflow_id}/history/{workflow_execution_id}",
)
def workflow_execution_timeline_page(
    request: Request,
    workflow_id: int,
    workflow_execution_id: str,
    session=Depends(require_page_session),
):
    """
    Render an operator-readable timeline for one persisted
    workflow execution.
    """

    from himp.api.workflows import workflow_history_service

    workflow_run = workflow_history_service.get(
        workflow_id,
        workflow_execution_id,
    )

    if workflow_run is None:
        raise HTTPException(
            status_code=404,
            detail="Workflow execution does not exist.",
        )

    context = dashboard_context()

    context["workflow_run"] = jsonable_encoder(
        workflow_run
    )
    context["workflow_actions_admin"] = (
        session.role == "admin"
    )

    return templates.TemplateResponse(
        request=request,
        name="workflow_execution_timeline.html",
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
    approval_status: str | None = None,
    schedule_status: str | None = None,
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

    if approval_status == "":
        approval_status = None

    if approval_status not in {
        None,
        "PENDING",
        "APPROVED",
        "DENIED",
    }:
        approval_status = None

    approval_result = (
        remediation_approval_service.list(
            limit=100,
            status=approval_status,
        )
    )

    context["remediation_approvals"] = (
        approval_result["approvals"]
    )
    context["remediation_approval_summary"] = (
        approval_result["summary"]
    )
    context["approval_status"] = (
        approval_status
    )


    if schedule_status == "":
        schedule_status = None

    if schedule_status not in {
        None,
        "SCHEDULED",
        "RUNNING",
        "COMPLETED",
        "FAILED",
        "CANCELLED",
    }:
        schedule_status = None

    remediation_schedule_result = (
        remediation_scheduling_service.list(
            limit=100,
            status=schedule_status,
        )
    )

    context["remediation_schedules"] = (
        remediation_schedule_result["schedules"]
    )

    context["remediation_schedule_summary"] = (
        remediation_schedule_result["summary"]
    )

    context["schedule_status"] = (
        schedule_status
    )

    context["remediation_schedule_map"] = {
        item["approval_id"]: item
        for item in remediation_schedule_result[
            "schedules"
        ]
    }

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
