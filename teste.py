"""Testes automáticos: sobem 3 servidores e o balanceador de verdade e conferem o comportamento.

Uso: python -m unittest teste -v
"""
import subprocess
import sys
import time
import unittest
import urllib.error
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

PASTA = Path(__file__).parent


def subir(*args):
    return subprocess.Popen([sys.executable, *args], cwd=PASTA, stdout=subprocess.DEVNULL)


def quem_atendeu(_=None):
    """Pede a página ao balanceador e devolve a porta do servidor que respondeu."""
    with urllib.request.urlopen("http://127.0.0.1:8000/", timeout=10) as r:
        return int(r.read().decode().split("servidor ")[1][:4])


class Base(unittest.TestCase):
    ALGORITMO = "round_robin"
    ATRASOS = {8001: "0", 8002: "0", 8003: "0"}

    def setUp(self):
        self.servidores = {p: subir("servidor.py", str(p), a) for p, a in self.ATRASOS.items()}
        self.lb = subir("balanceador.py", self.ALGORITMO)
        time.sleep(1.5)

    def tearDown(self):
        for processo in [self.lb, *self.servidores.values()]:
            processo.kill()
            processo.wait()

    def derrubar(self, porta):
        self.servidores[porta].kill()
        self.servidores[porta].wait()


class TesteRoundRobin(Base):
    def test_reveza_em_ordem(self):
        self.assertEqual([quem_atendeu() for _ in range(6)], [8001, 8002, 8003] * 2)

    def test_falha_e_volta(self):
        self.derrubar(8002)
        # Logo depois da queda, nenhum pedido se perde e o 8002 não aparece mais.
        self.assertEqual(set(quem_atendeu() for _ in range(6)), {8001, 8003})
        # Religado, a checagem de saúde (a cada 2 s) põe o 8002 de volta na roda.
        self.servidores[8002] = subir("servidor.py", "8002")
        time.sleep(3)
        self.assertIn(8002, [quem_atendeu() for _ in range(3)])

    def test_todos_fora_do_ar(self):
        for porta in list(self.servidores):
            self.derrubar(porta)
        with self.assertRaises(urllib.error.HTTPError) as erro:
            quem_atendeu()
        self.assertEqual(erro.exception.code, 503)


class TesteMenosConexoes(Base):
    ALGORITMO = "menos_conexoes"
    ATRASOS = {8001: "0.05", 8002: "0.05", 8003: "0.5"}  # o 8003 é uma máquina 10x mais lenta

    def test_servidor_lento_recebe_menos(self):
        with ThreadPoolExecutor(10) as grupo:
            contagem = Counter(grupo.map(quem_atendeu, range(60)))
        # No round robin cada um receberia 20. Aqui o lento fica ocupado e recebe bem menos.
        self.assertLess(contagem[8003], 10, contagem)


if __name__ == "__main__":
    unittest.main()
