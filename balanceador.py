"""Balanceador de carga do ShopNow.

Uso: python balanceador.py [round_robin | menos_conexoes]

O cliente acessa só a porta 8000. Para cada requisição o balanceador escolhe
um dos servidores (8001, 8002, 8003), repassa o pedido e devolve a resposta.
"""
import http.client
import json
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORTA = 8000
SERVIDORES = [8001, 8002, 8003]
ALGORITMOS = ["round_robin", "menos_conexoes"]
ALGORITMO = sys.argv[1] if len(sys.argv) > 1 else "round_robin"
if ALGORITMO not in ALGORITMOS:
    sys.exit(f"Algoritmo desconhecido: {ALGORITMO}. Use um destes: {', '.join(ALGORITMOS)}")

# Estado compartilhado. Cada requisição roda numa thread, então todo acesso passa pela trava.
vivos = set(SERVIDORES)                # servidores que estão respondendo
conexoes = {p: 0 for p in SERVIDORES}  # requisições em andamento agora em cada servidor
atendidas = {p: 0 for p in SERVIDORES} # total de requisições que cada servidor já respondeu
proximo = 0                            # contador do round robin
trava = threading.Lock()


def escolher():
    """Escolhe um servidor vivo segundo o algoritmo. Devolve None se todos caíram."""
    global proximo
    with trava:
        candidatos = [p for p in SERVIDORES if p in vivos]
        if not candidatos:
            return None
        if ALGORITMO == "round_robin":
            # Um de cada vez, em fila: 8001, 8002, 8003, 8001, ...
            porta = candidatos[proximo % len(candidatos)]
            proximo += 1
        else:
            # Menos conexões: quem está com menos requisições em andamento agora.
            porta = min(candidatos, key=lambda p: conexoes[p])
        conexoes[porta] += 1
        return porta


def repassar(porta, caminho):
    """Faz o mesmo pedido ao servidor escolhido. Lança erro se ele estiver fora do ar."""
    con = http.client.HTTPConnection("127.0.0.1", porta, timeout=5)
    try:
        con.request("GET", caminho)
        resposta = con.getresponse()
        return resposta.status, resposta.read()
    finally:
        con.close()
        with trava:
            conexoes[porta] -= 1  # o pedido terminou, com sucesso ou não


def verificar_saude():
    """A cada 2 segundos pergunta /saude a cada servidor: quem cai sai da lista, quem volta entra."""
    while True:
        for porta in SERVIDORES:
            try:
                con = http.client.HTTPConnection("127.0.0.1", porta, timeout=1)
                con.request("GET", "/saude")
                ok = con.getresponse().status == 200
                con.close()
            except (OSError, http.client.HTTPException):
                ok = False
            with trava:
                mudou = ok != (porta in vivos)
                if ok:
                    vivos.add(porta)
                else:
                    vivos.discard(porta)
            if mudou:
                print(f"[saude] servidor {porta} {'VOLTOU' if ok else 'CAIU'}")
        time.sleep(2)


class Servidor(ThreadingHTTPServer):
    request_queue_size = 128  # fila de conexões esperando; o padrão (5) recusa conexões sob carga


class Balanceador(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/status":
            with trava:
                dados = {"algoritmo": ALGORITMO, "vivos": sorted(vivos),
                         "atendidas": atendidas, "em_andamento": conexoes}
                corpo = json.dumps(dados, indent=2).encode()
            return self.responder(200, corpo, "application/json")

        for _ in SERVIDORES:  # tenta no máximo uma vez cada servidor
            porta = escolher()
            if porta is None:
                break
            try:
                status, corpo = repassar(porta, self.path)
            except (OSError, http.client.HTTPException):
                # O servidor caiu entre uma checagem de saúde e outra: tira da lista
                # na hora e tenta o próximo. O cliente nem percebe a falha.
                with trava:
                    vivos.discard(porta)
                print(f"[falha] servidor {porta} não respondeu; pedido reenviado a outro")
                continue
            with trava:
                atendidas[porta] += 1
            return self.responder(status, corpo)

        self.responder(503, "Nenhum servidor disponível".encode())

    def responder(self, status, corpo, tipo="text/html; charset=utf-8"):
        self.send_response(status)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)

    def log_message(self, *args):
        pass  # sem um print por requisição: no teste de carga seriam milhares de linhas


threading.Thread(target=verificar_saude, daemon=True).start()
print(f"Balanceador na porta {PORTA} usando {ALGORITMO} para {SERVIDORES}")
try:
    Servidor(("127.0.0.1", PORTA), Balanceador).serve_forever()
except KeyboardInterrupt:
    print("Balanceador desligado")
