# 🚀 Quick Start Guide - RAG Chatbot

## ✅ Setup Complete Checklist:
- ✅ Ollama installed
- ✅ Python packages installed
- ✅ GROQ_API_TOKEN configured
- ✅ Test passed

---

## 🎯 How to Start Everything (Step-by-Step)

### **Step 1: Pull Ollama Embedding Model**
Open **PowerShell** and run:
```powershell
ollama pull nomic-embed-text
```

Wait for download to complete (should show: "success")

### **Step 2: Start Ollama Server**
Keep the **same PowerShell terminal** open and run:
```powershell
ollama serve
```

**IMPORTANT:** This terminal must stay open! You'll see:
```
Listening on 127.0.0.1:11434
```

**⚠️ Don't close this terminal!**

### **Step 3: Start Flask Application**
Open a **NEW PowerShell terminal** (keep first one running) and run:
```powershell
cd C:\Users\rucha\Downloads\Project\STEP_8_APPLICATION
python app.py
```

You should see:
```
* Running on http://127.0.0.1:5000
* Running on http://127.0.0.1:5000 (Press CTRL+C to quit)
```

### **Step 4: Open Browser**
Open your browser and go to:
```
http://127.0.0.1:5000
```

---

## 💬 Using the RAG Chatbot

### **In the Browser:**

1. **Find the Button:**
   Look for the **blue button** that says:
   ```
   💬 AI Document Chat [PDF Q&A]
   ```

2. **Click the Button:**
   A modal window will open

3. **Upload PDF:**
   - Click "Choose File"
   - Select any PDF (borewell report, research paper, etc.)
   - Click "📄 Process PDF"
   - Wait for: "✅ PDF processed successfully!"

4. **Ask Questions:**
   - Type your question in the input box
   - Examples:
     * "What is this document about?"
     * "What is the recommended depth?"
     * "Summarize the main points"
   - Press "Send" or hit Enter

5. **Get Answers:**
   - AI will respond based on the PDF content
   - You can ask follow-up questions
   - Chat history is maintained

---

## 🧪 Test with Sample Questions

### **If you upload a borewell guideline PDF:**
```
You: What is the recommended depth for borewells?
AI: [Answer based on PDF content]

You: What about water quality testing?
AI: [Answer based on PDF content]

You: How much spacing is required?
AI: [Answer based on PDF content]
```

### **If you upload a research paper:**
```
You: What is this paper about?
AI: [Summary from PDF]

You: What are the main findings?
AI: [Key findings from PDF]

You: Tell me more about the methodology
AI: [Methodology details from PDF]
```

---

## 🔧 Troubleshooting

### **Problem: "Failed to create embeddings"**
**Solution:**
1. Make sure Ollama is running: `ollama serve`
2. Check model is downloaded: `ollama list`
3. Should see `nomic-embed-text` in the list

### **Problem: "Please upload a PDF first"**
**Solution:**
- Make sure you clicked "📄 Process PDF" button
- Wait for success message before asking questions

### **Problem: Port already in use**
**Solution:**
- Close any other Flask apps running
- Or change port in app.py: `app.run(debug=True, port=5001)`

---

## 📊 Terminal Layout (How it should look)

### **Terminal 1 (Ollama Server):**
```powershell
PS C:\> ollama serve
time=2025-10-15T10:30:00.000+05:30 level=INFO source=server.go:158 msg="Listening on 127.0.0.1:11434"
```
**⚠️ Keep this running!**

### **Terminal 2 (Flask App):**
```powershell
PS C:\Users\rucha\Downloads\Project\STEP_8_APPLICATION> python app.py
✅ Loaded 30 borewells from CGWB database
 * Serving Flask app 'app'
 * Debug mode: on
WARNING: This is a development server.
 * Running on http://127.0.0.1:5000
Press CTRL+C to quit
```
**⚠️ Keep this running too!**

### **Browser:**
```
http://127.0.0.1:5000
↓
Main Page Opens
↓
Click "💬 AI Document Chat" button
↓
Upload PDF & Ask Questions!
```

---

## 🎨 What You'll See in UI

### **Main Page:**
- Normal groundwater prediction interface
- **NEW:** Blue button "💬 AI Document Chat [PDF Q&A]"

### **Modal Window:**
```
╔══════════════════════════════════════════╗
║  💬 AI Document Chat                     ║
║  Upload PDF and ask questions using RAG  ║
╠══════════════════════════════════════════╣
║  📄 Upload PDF Document                  ║
║  [Choose File] ← Select your PDF         ║
║  [📄 Process PDF] ← Click to upload      ║
║  ✅ PDF processed: 15 pages              ║
║                                          ║
║  Chat Area (appears after upload):       ║
║  ┌────────────────────────────────────┐ ║
║  │ You: What is this about?           │ ║
║  │ 🤖 AI: According to document...    │ ║
║  └────────────────────────────────────┘ ║
║                                          ║
║  [Type question...] [Send] [Clear]      ║
╚══════════════════════════════════════════╝
```

---

## ✨ Quick Command Reference

```powershell
# Start Ollama (Terminal 1)
ollama serve

# Start Flask App (Terminal 2)
cd C:\Users\rucha\Downloads\Project\STEP_8_APPLICATION
python app.py

# Browser
http://127.0.0.1:5000

# Stop Servers (when done)
CTRL+C in both terminals
```

---

## 🎯 Next Steps

1. ✅ Start Ollama server (`ollama serve`)
2. ✅ Start Flask app (`python app.py`)
3. ✅ Open browser (http://127.0.0.1:5000)
4. ✅ Click "💬 AI Document Chat" button
5. ✅ Upload a PDF and test!

---

## 📞 Need Help?

If something doesn't work:
1. Check both terminals are running
2. Check no errors in Flask terminal
3. Check browser console (F12) for JavaScript errors
4. Try with a different PDF (simpler one first)

---

**Ready to start? Follow Step 1-4 above! 🚀**
