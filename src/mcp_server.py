#!/usr/bin/env python3
"""
Ulak Haberleşme Rapor MCP Server
Claude CLI'nin -p çağrıları sırasında kullanabileceği araçları sağlar.
Başlatma: python src/mcp_server.py  (stdio üzerinden iletişim kurar)
"""
import asyncio
import json
import sys
from pathlib import Path

# Proje kökünü sys.path'e ekle (MCP server bağımsız süreç olarak başlar)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

from src.database import init_db, sentiment_trend_al, url_mevcut_mu, son_haberler_al
from src.crawler_agent import ddg_ara, sayfa_metni_cek
from config.settings import ARAMA_KATEGORILERI

server = Server("ulak-tools")


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="search_company_news",
            description=(
                "İnternette Ulak Haberleşme ile ilgili haberleri DuckDuckGo'da arar. "
                "Başlık, URL, kaynak ve tarih bilgisi döner."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Arama sorgusu (örn: 'Ulak Haberleşme 5G 2025')",
                    },
                    "days": {
                        "type": "integer",
                        "description": "Kaç günlük haber aransın (varsayılan: 7)",
                        "default": 7,
                    },
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="crawl_page",
            description=(
                "Bir URL'yi ziyaret eder ve makale ana metnini çeker. "
                "Haberin tam içeriğine ihtiyaç duyulduğunda kullanılır."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "Ziyaret edilecek haber URL'si",
                    },
                },
                "required": ["url"],
            },
        ),
        types.Tool(
            name="get_sentiment_trend",
            description=(
                "Geçmiş haftaların sentiment dağılımını döner. "
                "Medya tonunun değişimini analiz etmek için kullanılır."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "weeks": {
                        "type": "integer",
                        "description": "Kaç haftalık geçmiş (varsayılan: 4)",
                        "default": 4,
                    },
                },
            },
        ),
        types.Tool(
            name="check_url_exists",
            description="Bir haberin daha önce işlenip veritabanına kaydedilip kaydedilmediğini kontrol eder.",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "Kontrol edilecek URL",
                    },
                },
                "required": ["url"],
            },
        ),
        types.Tool(
            name="get_recent_news",
            description="Veritabanındaki son N günün haberlerini döner.",
            inputSchema={
                "type": "object",
                "properties": {
                    "days": {
                        "type": "integer",
                        "description": "Kaç günlük haber (varsayılan: 7)",
                        "default": 7,
                    },
                },
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name == "search_company_news":
        sorgu = arguments["query"]
        gun = arguments.get("days", 7)
        sonuclar = ddg_ara(sorgu, gun)
        return [types.TextContent(
            type="text",
            text=json.dumps(sonuclar[:10], ensure_ascii=False, default=str),
        )]

    if name == "crawl_page":
        url = arguments["url"]
        metin = sayfa_metni_cek(url)
        return [types.TextContent(
            type="text",
            text=metin[:4000] if metin else "Sayfa içeriği çekilemedi.",
        )]

    if name == "get_sentiment_trend":
        hafta = arguments.get("weeks", 4)
        trend = sentiment_trend_al(hafta)
        return [types.TextContent(
            type="text",
            text=json.dumps(trend, ensure_ascii=False),
        )]

    if name == "check_url_exists":
        url = arguments["url"]
        return [types.TextContent(
            type="text",
            text="evet" if url_mevcut_mu(url) else "hayır",
        )]

    if name == "get_recent_news":
        gun = arguments.get("days", 7)
        haberler = son_haberler_al(gun)
        return [types.TextContent(
            type="text",
            text=json.dumps(haberler, ensure_ascii=False, default=str),
        )]

    raise ValueError(f"Bilinmeyen araç: {name}")


async def main():
    init_db()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
