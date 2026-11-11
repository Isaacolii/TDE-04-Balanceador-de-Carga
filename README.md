# TDE 04 — Balanceador de carga do ShopNow

Três instâncias do site da ShopNow e um balanceador de carga na frente delas, em Python
puro (só a biblioteca padrão, nada para instalar além do Python 3).

```
                         ┌──────────────► servidor 8001
cliente ──► balanceador ─┼──────────────► servidor 8002
            (porta 8000) └──────────────► servidor 8003 (mais lento)
```

O cliente só conhece a porta 8000. O balanceador escolhe um servidor para cada pedido,
repassa, e devolve a resposta. Se um servidor cai, ele sai da lista e os pedidos vão para os
outros; quando volta, entra de novo sozinho.

## Arquivos

| Arquivo          | O que faz                                                              |
|------------------|------------------------------------------------------------------------|
| `servidor.py`    | Uma instância do site. Rota `/` (a página) e `/saude` (estou vivo).    |
| `balanceador.py` | Recebe na porta 8000, escolhe o servidor e repassa. Rota `/status`.    |
| `iniciar.bat`    | Abre os 3 servidores e o balanceador, cada um numa janela.             |
| `teste.py`       | Testes automáticos de revezamento, falha, retorno e menos conexões.    |

## Algoritmos

- **round_robin** — um de cada vez, em ordem: 8001, 8002, 8003, 8001...
- **menos_conexoes** — manda para o servidor com menos pedidos em andamento naquele momento.

## Como rodar

```bat
iniciar.bat                  :: round robin
iniciar.bat menos_conexoes   :: menos conexões
```

Ou à mão, cada linha num terminal:

```bat
python servidor.py 8001 0.05
python servidor.py 8002 0.05
python servidor.py 8003 0.2
python balanceador.py round_robin
```

O segundo número é o atraso por página em segundos. O 8003 tem 0.2 para fazer o papel de uma
máquina mais fraca, e é isso que mostra a diferença entre os dois algoritmos.

Depois abra `http://127.0.0.1:8000/` e recarregue: cada vez atende um servidor diferente.
`http://127.0.0.1:8000/status` mostra quem está vivo e quantos pedidos cada um atendeu.

## Simular falha

Feche a janela do `Servidor 8002` (ou Ctrl+C nela). O balanceador escreve
`[saude] servidor 8002 CAIU` e o site continua no ar com os outros dois. Para religar:

```bat
python servidor.py 8002 0.05
```

Em até 2 segundos aparece `[saude] servidor 8002 VOLTOU`.

## Teste de carga com Apache Benchmark

```bat
ab -n 2000 -c 50 http://127.0.0.1:8000/
```

`-n 2000` pedidos no total, `-c 50` ao mesmo tempo. Usar `127.0.0.1`, não `localhost`.
No Windows o `ab.exe` vem na pasta `bin` do pacote do Apache da Apache Lounge; no Linux, no
pacote `apache2-utils`.

Resultados medidos (Windows 11, servidores com atraso 0.05 / 0.05 / 0.2 s):

| Cenário                                    | Pedidos/s | Falhas | 8001 | 8002 | 8003 |
|--------------------------------------------|----------:|-------:|-----:|-----:|-----:|
| round_robin, 2000 pedidos                  |       456 |      0 |  667 |  667 |  666 |
| menos_conexoes, 2000 pedidos               |       644 |      0 |  893 |  880 |  227 |
| round_robin, 3000 pedidos, 8002 cai no meio |      413 |      0 | 1267 |  467 | 1266 |
| menos_conexoes, 3000 pedidos, 8002 cai no meio | 627 |      0 | 1665 |  897 |  438 |

- O round robin divide igual, mesmo o 8003 sendo 4x mais lento, e os pedidos que caem nele
  seguram o teste. O menos conexões percebe que o 8003 vive ocupado e manda menos para ele:
  cerca de 40% mais pedidos por segundo.
- Com o 8002 derrubado no meio da carga, nenhum dos 3000 pedidos falhou: os que estavam indo
  para ele foram reenviados a outro servidor.

## Testes automáticos

```bat
python -m unittest teste -v
```
