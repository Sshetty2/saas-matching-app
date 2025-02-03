# SaaS Installed Apps Scanner

A **Streamlit-powered** application that scans installed software and matches them against the **National Vulnerability Database (NVD)** using **AI-powered analysis**.

---

## **🔍 Overview**
This application **processes installed software from computers** and attempts to match them with **official Common Platform Enumeration (CPE) entries** in the **NVD database**.  
It leverages **GPT-4o-mini** for **software name normalization**, **semantic similarity ranking**, and **confidence-based match analysis**.

---

## **🚀 Key Features**
**SQL Server Integration** → Fetches installed applications per **computer & scan ID**  
**NVD API Integration** → Queries **NVD’s CPE database** for vulnerability matches  
**AI-Powered Software Normalization** → Uses **GPT-4o-mini** to clean and standardize software names  
**Semantic Similarity Matching** → **Cosine similarity** ranking for top 3 CPE matches  
**Confidence-Based Analysis** → GPT-4o-mini rates, ranks, and reviews CPE matches  
**Real-Time Progress Tracking** → UI updates as processing happens  
**Error Logging & Display** → Handles API failures and processing errors  

---

## **⚙️ Application Flow**
1. **Database Query** 🏛️  
   - Retrieves **installed software** for a selected **Computer & Scan ID**
  
2. **Software Name Normalization** 🤖  
   - Uses **GPT-4o-mini** to clean and standardize software names  
   - Removes **unnecessary details** (e.g., versions, platform identifiers)  

3. **NVD API Querying** 🌐  
   - Searches **CPE database** using **cleaned query text**  
   - URL encoding ensures compatibility with **NVD search behavior**  

4. **CPE Match Ranking** 📊  
   - **Top 3 CPE matches** are ranked using **cosine similarity**  

5. **AI-Powered Match Analysis** 🔍  
   - GPT-4o-mini **rates, ranks, and reviews** the matches  
   - Assigns a **confidence score** with **explanations**  

6. **Results Display** 🖥️  
   - The UI **updates in real-time** as software is processed  

---

## **📌 Control Flow Diagram**
Below is a **visual representation** of how the app processes software and retrieves NVD matches.

![Control Flow Diagram](docs/control_flow_diagram.png)  

---

## **🛠️ Key Components**
### **📂 Database Operations**
| Function | Description |
|----------|------------|
| `get_computers()` | Retrieves list of available computers |
| `get_scan_ids(computer_name)` | Fetches available scan IDs for the selected computer |
| `get_installed_apps(computer_name, scan_id, limit)` | Fetches installed software for a given scan ID |

### **🤖 AI Processing**
| Function | Description |
|----------|------------|
| `generate_nvd_query_text(software_name)` | Calls **GPT-4o-mini** to clean and standardize the software name |
| `get_best_cpe_matches(query_text, full_query)` | Queries **NVD API** and ranks the **top 3** CPE matches |
| `analyze_cpe_matches(full_query, cpe_results)` | Uses **GPT-4o-mini** to **rate, rank, and explain** CPE matches |

### **🌐 NVD API Integration**
| Feature | Implementation |
|---------|---------------|
| **Search Query Handling** | Uses **`urllib.parse.quote_plus()`** for proper encoding |
| **Rate Limiting** | Ensures **6-second intervals** between requests |
| **Error Handling** | Logs **failed API requests** and displays errors in the UI |

---

## **📥 Installation**
### **Prerequisites**
- **Python 3.13+**
- **SQL Server with ODBC Driver 17**
- **OpenAI API Key**
- **(Optional) NVD API Key**

### **🔧 Setup Instructions**
1️⃣ **Clone the repository**
```bash
   git clone https://github.com/sshetty/saas-matching-app.git
   cd saas-scanner
   pip install -r requirements.txt
```

2️⃣ **Set up environment variables**
    Create a `.env` file in the root directory and add the following variables:

```bash
    DB_DATABASE=your_database_name
    OPENAI_API_KEY=your_openai_api_key
    NVD_API_KEY=your_nvd_api_key
```

3️⃣ **Run the application**
```bash
    streamlit run streamlit_app.py
```

