import asyncio
import asyncpg

async def run():
    conn = await asyncpg.connect(user='admin', password='2Cents#101',
                                 database='qdb', host='62.72.42.9',port=8812)
    values = await conn.fetch(
        'SELECT * FROM AAPL' 
    )
    print(len(values))
    await conn.close()

asyncio.run(run())