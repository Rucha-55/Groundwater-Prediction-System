# 🚀 SIMPLIFIED START GUIDE - No Ollama Required!

## ✨ Alternative Solution: Use Sentence Transformers (Local & Free)

Since Ollama path issues exist, we'll use **Sentence Transformers** instead - it's purely Python-based and easier!

---

## 📦 Step 1: Install Sentence Transformers

```powershell
pip install sentence-transformers
```

---

## 🎯 Step 2: Start Flask App Directly

```powershell
cd C:\Users\rucha\Downloads\Project\STEP_8_APPLICATION
python app.py
```

---

## 🌐 Step 3: Open Browser

```
http://127.0.0.1:5000
```

---

## 💬 Step 4: Use RAG Chatbot

1. Click "💬 AI Document Chat" (blue button)
2. Upload PDF
3. Ask questions!

---

## 📝 Alternative: Run Ollama with Full Path

If you want to use Ollama, use the full path:

### **Terminal 1 - Start Ollama:**
```powershell
& "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" serve
```

### **Terminal 2 - Pull Model:**
```powershell
& "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" pull nomic-embed-text
```

### **Terminal 3 - Start Flask:**
```powershell
cd C:\Users\rucha\Downloads\Project\STEP_8_APPLICATION
python app.py
```

---

## ✅ Recommended: Use Sentence Transformers (Easier!)

I'll update the code to use Sentence Transformers instead of Ollama.
This is better because:
- ✅ No separate server needed
- ✅ Works directly in Python
- ✅ Free and fast
- ✅ No PATH issues

---

Choose one option:
1. **Easy Way:** Install sentence-transformers (I'll update code)
2. **Ollama Way:** Use full paths shown above
