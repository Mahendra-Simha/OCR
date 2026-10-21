Project Overview: Scanned PDF OCR Extractor
Description:
A lightweight, high-performance web application designed to extract editable text from scanned PDF documents using Optical Character Recognition (OCR). The application is specifically hardware-optimized to run stably on standard laptops without crashing due to memory limits or CPU overheating.

Primary Use Case:
Assisting transcriptionists in rapidly converting scanned medical records or documents into searchable, editable text formats.

🛠️ Technology Stack
Backend Framework: Python with FastAPI (for asynchronous API handling).

OCR Engine: Tesseract OCR (via pytesseract).

PDF Processing: Poppler (via pdf2image for converting PDF pages to images).

Frontend UI: HTML5, Vanilla JavaScript, and Tailwind CSS (via CDN).

Document Generation: docx.js (for client-side .docx generation).

✨ Key Features Developed
1. Hardware-Optimized Processing
The backend is specifically engineered to survive on a machine with 8GB RAM and an Intel i5 (U-series) processor:

Concurrency Limits: Utilizes a ThreadPoolExecutor locked to a maximum of 2 concurrent workers. This mathematically prevents the application from consuming all 8GB of RAM, preventing system crashes.

CPU Thermal Management: Downscales PDF images to 150 DPI and converts them to grayscale before feeding them to the OCR engine. This drastically reduces the mathematical load on the CPU, preventing thermal throttling.

Optimized AI Model: Configured to use the Tesseract "Fast" language model (tessdata_fast) for significantly faster extraction times with minimal accuracy loss.

2. Intelligent Background Processing & Polling
PDFs are processed asynchronously in the background.

The frontend polls the /status/{task_id} endpoint every 2 seconds.

Provides a smooth, real-time progress bar displaying exact page completion (e.g., "14 out of 50 is processed").

3. Graceful Cancellation
Users can halt the extraction process midway using a "Stop Extraction" button.

The backend actively listens for cancellation flags. If stopped, it gracefully exits the loop, saves the text extracted up to that exact moment, and safely deletes temporary files from the SSD.

4. Interactive "Find & Highlight" Feature
A real-time search bar that triggers on every keystroke (oninput).

Uses a complex dual-layer HTML trick: A hidden backdrop layer renders a bright yellow <mark> tag precisely behind the matched word in the transparent foreground <textarea>.

Automatically scrolls to the matched word without interrupting the user's typing focus.

5. Multi-Format Export
Copy: One-click copy to the system clipboard.

TXT Export: Generates a lightweight .txt file.

DOCX Export: Uses docx.js to compile the extracted text into a native Microsoft Word document directly in the browser, preserving line breaks.

6. Custom UI & Experience
Clean, modern interface built with Tailwind CSS.

Replaced all default browser alert popups with custom, frosted-glass modal dialogs tailored for Errors, Warnings, and Info.

Dynamic page breaks automatically inserted into the text output (e.g., --- Page 4 ---).

📂 Architecture & File Structure
The project consists of two main files:

1. main.py (The Backend)
Handles the routing and heavy lifting.

/upload: Accepts the PDF, saves it temporarily to the SSD, assigns a UUID task ID, and triggers the background background process.

/status/{task_id}: Returns the current page-by-page progress or completion state.

/cancel/{task_id}: Intercepts a running task and flags it to stop.

process_pdf_in_batches(): The core background engine that slices the PDF into 10-page chunks, runs the concurrent OCR, tracks the page numbers, and performs SSD cleanup.

2. templates/index.html (The Frontend)
Handles the user interface and client-side logic.

Custom Modal HTML/JS: For displaying beautiful alerts.

Polling Logic: pollServerForProgress() function to request status updates.

Search Logic: findWordInText(), syncScroll(), and syncText() which manage the real-time background highlighting.

Export Logic: JavaScript Blobs utilized to generate downloadable files without needing to send data back to the server.

🔒 Security & Deployment Note (HIPAA Compliance)
Due to the target audience (Transcriptionists handling medical records), this application handles Protected Health Information (PHI).

Current State: The application lacks authentication, audit logging, and secure data-at-rest deletion protocols required for cloud hosting.

Deployment Strategy: To remain 100% free and HIPAA compliant, this application is designed to be run locally (localhost) on the transcriptionist's physical, employer-secured computer. Because the PDFs never leave their local hard drive and are not transmitted over the open internet, it circumvents the need for expensive, BAA-signed cloud hosting infrastructure.