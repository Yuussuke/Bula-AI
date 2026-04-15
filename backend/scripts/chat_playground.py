import asyncio
import sys
import os

# Esse bloco evita o erro "No module named 'app'"
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_core.messages import HumanMessage
from app.modules.rag.llm import get_maritalk


async def main():
    print("Iniciando conexão com a Maritalk...")
    llm = get_maritalk(model_name="sabiazinho-4")

    while True:
        query = input("\nPergunta (ou 'sair'): ")
        if query.lower() == "sair":
            break

        response = await llm.ainvoke([HumanMessage(content=query)])
        print(f"\nSabiá: {response.content}")


if __name__ == "__main__":
    asyncio.run(main())
