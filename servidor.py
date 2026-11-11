"""Uma instância do site ShopNow.

Uso:     python servidor.py <porta> [atraso_em_segundos]
Exemplo: python servidor.py 8001 0.05

Rodando três vezes, com portas diferentes, temos três cópias do mesmo site.
"""
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORTA = int(sys.argv[1])
ATRASO = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0


class Servidor(ThreadingHTTPServer):
    request_queue_size = 128  # fila de conexões esperando; o padrão (5) recusa conexões sob carga


class Site(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/saude":
            corpo = b"OK"  # resposta curta para o balanceador saber que estamos vivos
        else:
            time.sleep(ATRASO)  # simula o trabalho de montar a página (banco, estoque, preço)
            corpo = f"<h1>ShopNow</h1><p>Atendido pelo servidor {PORTA}</p>".encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)

    def log_message(self, *args):
        pass  # sem um print por requisição: no teste de carga seriam milhares de linhas


print(f"Servidor ShopNow na porta {PORTA} (atraso de {ATRASO}s por página)")
try:
    Servidor(("127.0.0.1", PORTA), Site).serve_forever()
except KeyboardInterrupt:
    print(f"Servidor {PORTA} desligado")
