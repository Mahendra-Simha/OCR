import uuid
import os
import asyncio
import concurrent.futures
from fastapi import FastAPI, UploadFile, File, BackgroundTasks, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pdf2image import convert_from_path, pdfinfo_from_path
import pytesseract

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Update this path to where your poppler bin folder is!
POPPLER_PATH = r'C:\poppler\Library\bin' 
# ADD THIS LINE FOR TESSERACT:
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# In-memory dictionary to track progress
tasks = {}

def extract_text_sync(image):
    """Synchronous helper function for ThreadPoolExecutor to run OCR."""
    return pytesseract.image_to_string(image)

async def process_pdf_in_batches(task_id: str, file_path: str):
    """Background task optimized for 8GB RAM and i5 Processor with Stop functionality."""
    try:
        # 1. Get the total number of pages quickly
        info = await asyncio.to_thread(pdfinfo_from_path, file_path, poppler_path=POPPLER_PATH)
        total_pages = info["Pages"]
        tasks[task_id]["total"] = total_pages
        
        extracted_text_list = []
        chunk_size = 10 
        
        loop = asyncio.get_running_loop()
        
        # 2. Batch-processing loop
        for start_page in range(1, total_pages + 1, chunk_size):
            
            # --- CANCELLATION CHECK 1: Before starting a new 10-page chunk ---
            if tasks[task_id].get("status") == "cancelled":
                break
                
            end_page = min(start_page + chunk_size - 1, total_pages)
            
            # Convert PDF to images
            images = await asyncio.to_thread(
                convert_from_path, 
                file_path, 
                first_page=start_page, 
                last_page=end_page, 
                poppler_path=POPPLER_PATH,
                dpi=150,           
                grayscale=True,    
                thread_count=1     
            )
            
            chunk_texts = [None] * len(images)
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                futures = []
                for idx, image in enumerate(images):
                    future = loop.run_in_executor(pool, extract_text_sync, image)
                    futures.append((idx, future))
                
                for idx, future in futures:
                    # --- CANCELLATION CHECK 2: Between individual pages ---
                    if tasks[task_id].get("status") == "cancelled":
                        break
                        
                    text = await future
                    current_page_number = start_page + idx
                    
                    chunk_texts[idx] = text + f"\n\n--- Page {current_page_number} ---\n\n"
                    tasks[task_id]["progress"] = current_page_number
            
            # Filter out any 'None' values if the loop broke early due to cancellation
            valid_texts = [t for t in chunk_texts if t is not None]
            extracted_text_list.extend(valid_texts)
            
            # --- CANCELLATION CHECK 3: Exit the main chunk loop ---
            if tasks[task_id].get("status") == "cancelled":
                break
                
        # 3. Cleanup and mark as complete (if not cancelled)
        if tasks[task_id]["status"] != "cancelled":
            tasks[task_id]["status"] = "completed"
            
        # Save whatever text was extracted, even if it was stopped halfway
        tasks[task_id]["text"] = "".join(extracted_text_list)
        
    except Exception as e:
        tasks[task_id]["status"] = "failed"
        tasks[task_id]["error"] = str(e)
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

@app.get("/", response_class=HTMLResponse)
async def serve_frontend(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.post("/upload")
async def upload_pdf(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    # Generate a unique ID for this job
    task_id = str(uuid.uuid4())
    
    # Save the massive PDF to the hard drive temporarily (prevents RAM crashes)
    file_path = f"temp_{task_id}.pdf"
    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())
        
    # Initialize the tracker
    tasks[task_id] = {"status": "processing", "progress": 0, "total": 1, "text": ""}
    
    # Fire off the background task (FastAPI won't wait for this to finish)
    background_tasks.add_task(process_pdf_in_batches, task_id, file_path)
    
    # Immediately return the ticket ID to the frontend
    return JSONResponse({"task_id": task_id})

@app.get("/status/{task_id}")
async def get_status(task_id: str):
    """Frontend calls this every few seconds to check progress."""
    if task_id not in tasks:
        return JSONResponse({"error": "Task not found"}, status_code=404)
    return JSONResponse(tasks[task_id])

@app.post("/cancel/{task_id}")
async def cancel_task(task_id: str):
    """Endpoint for the user to stop an ongoing extraction."""
    if task_id not in tasks:
        return JSONResponse({"error": "Task not found"}, status_code=404)
    
    # Only cancel if it is currently running
    if tasks[task_id]["status"] == "processing":
        tasks[task_id]["status"] = "cancelled"
        return JSONResponse({"message": "Task cancellation requested. Stopping..."})
        
    return JSONResponse({"message": f"Cannot cancel. Task is already {tasks[task_id]['status']}."})