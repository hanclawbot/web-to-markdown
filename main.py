from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import requests
from bs4 import BeautifulSoup
import markdownify
import re
import os

app = FastAPI()

# 挂载静态文件
app.mount("/static", StaticFiles(directory="static"), name="static")

class URLRequest(BaseModel):
    url: str

def clean_html(html_content):
    """清理 HTML，移除脚本、样式等不需要的内容"""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # 移除不需要的标签
    for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'iframe', 'noscript']):
        tag.decompose()
    
    # 移除带有广告相关的 class 或 id
    for tag in soup.find_all(True):
        classes = tag.get('class', []) or []
        ids = tag.get('id', []) or []
        # 確保 class 和 id 都是列表
        if isinstance(classes, str):
            classes = [classes]
        if isinstance(ids, str):
            ids = [ids]
        combined = ' '.join(classes + ids).lower()
        if any(word in combined for word in ['ad', 'advertisement', 'banner', 'sidebar', 'menu', 'comment', 'social', 'share']):
            tag.decompose()
    
    return str(soup)

@app.get("/")
async def read_root():
    return FileResponse("static/index.html")

@app.post("/convert")
async def convert_url(request: URLRequest):
    try:
        # 获取网页内容
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(request.url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # 清理 HTML
        cleaned_html = clean_html(response.text)
        
        # 转换为 Markdown
        md = markdownify.markdownify(cleaned_html, heading_style="ATX")
        
        # 清理多余的空行
        md = re.sub(r'\n{3,}', '\n\n', md)
        md = md.strip()
        
        return {
            "success": True,
            "markdown": md,
            "title": BeautifulSoup(response.text, 'html.parser').title.string if BeautifulSoup(response.text, 'html.parser').title else "untitled"
        }
        
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=400, detail=f"无法获取网页: {str(e)}")
    except Exception as e:
        import traceback
        raise HTTPException(status_code=500, detail=f"转换失败: {str(e)}\n{traceback.format_exc()}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
