from fastapi import APIRouter, Request, HTTPException, Form
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, FileResponse
from fastapi.templating import Jinja2Templates
import json
from apps.util.config import get_redis_conn, get_postgres_conn, load_config
from apps.util.logger import make_logger
from apps.util.faults import set_fault

router = APIRouter()
config = load_config()
logger = make_logger("Route")

SITE_GRAPH_PATH = "/home/pmikol/projects/wireless-sensor-mesh-daq/dataserver/apps/site_graph_TEST.json"
templates = Jinja2Templates(directory="/home/pmikol/projects/wireless-sensor-mesh-daq/dataserver/apps/templates")

def normalize_mac(raw):
    try:
        value = int(raw, 16)
        hex_str = f"{value:012x}"
        return ":".join(hex_str[i:i+2] for i in range(0, 12, 2))
    except ValueError:
        return "invalid"

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("sitedata/dashboard.html", {"request": request})

@router.get("/sitearray/map", response_class=HTMLResponse)
async def mapviewer(request: Request):
    return templates.TemplateResponse("sitedata/mapviewer.html", {"request": request})

@router.get("/sitearray/map/layout", response_class=JSONResponse)
async def get_panel_layout():
    try:
        pg = get_postgres_conn()
        with pg.cursor() as cur:
            cur.execute("""
                SELECT sg.json
                FROM ss.site_graph sg
                JOIN ss.site_array sa ON sg.sitearray_id = sa.id
                JOIN ss.site s ON s.id = sa.site_id
                WHERE s.sitename = %s
            """, ('TEST',))
            result = cur.fetchone()
            if not result:
                raise HTTPException(status_code=404, detail="Site graph not found")

            graph_json = json.loads(result[0])
            layout = []

            def walk(node):
                if not isinstance(node, dict):
                    return
                if node.get("devtype") == "P":
                    x = node.get("x")
                    y = node.get("y")
                    inputs = node.get("inputs", [])
                    mac = inputs[0].get("macaddr", "").lower()
                    if mac and x is not None and y is not None:
                        layout.append({"mac": mac, "x": x, "y": y})
                for child in node.get("inputs", []):
                    walk(child)

            walk(graph_json.get("sitearray", {}))
            return JSONResponse(content=layout)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {e}")

@router.get("/sitearray/map/status", response_class=JSONResponse)
async def sitearray_map_status():
    try:
        redis_conn = get_redis_conn(db=3)
        pg = get_postgres_conn()

        with pg.cursor() as cur:
            cur.execute("""
                SELECT sg.json
                FROM ss.site_graph sg
                JOIN ss.site_array sa ON sg.sitearray_id = sa.id
                JOIN ss.site s ON sa.site_id = s.id
                WHERE s.sitename = %s
            """, ('TEST',))
            result = cur.fetchone()
            if not result:
                raise HTTPException(status_code=404, detail="Site graph not found")
            graph_json = json.loads(result[0])

        layout = {}
        def walk(node):
            if not isinstance(node, dict):
                return
            if node.get("devtype") == "P":
                x = node.get("x")
                y = node.get("y")
                inputs = node.get("inputs", [])
                mac = inputs[0].get("macaddr", "").lower()
                if mac and x is not None and y is not None:
                    layout[mac] = {"x": x, "y": y}
            for child in node.get("inputs", []):
                walk(child)

        walk(graph_json.get("sitearray", {}))

        response = []
        for key in redis_conn.scan_iter("sitearray:monitor:*"):
            mac = key.split(":", 2)[2].lower()
            data = redis_conn.hgetall(key)
            panel_info = layout.get(mac)

            if panel_info:
                response.append({
                    "mac": mac,
                    "status": data.get("status", "unknown"),
                    "voltage": data.get("voltage"),
                    "current": data.get("current"),
                    "x": panel_info["x"],
                    "y": panel_info["y"]
                })

        return JSONResponse(content=response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {e}")

@router.get("/site_graph_TEST.json")
async def get_site_graph():
    return FileResponse(SITE_GRAPH_PATH)

@router.post("/api/inject_fault")
async def inject_fault(mac: str = Form(...), fault: str = Form(...)):
    try:
        set_fault(mac, fault)
        return PlainTextResponse(f"Injected '{fault}' into {mac}")
    except Exception as e:
        return PlainTextResponse(f"Error: {e}", status_code=500)

@router.post("/api/clear_all_faults")
async def clear_all_faults():
    try:
        r = get_redis_conn(db=3)
        keys = r.keys("fault_injection:*")
        if keys:
            r.delete(*keys)
        return PlainTextResponse("✅ All faults cleared.")
    except Exception as e:
        return PlainTextResponse(f"Error: {e}", status_code=500)
