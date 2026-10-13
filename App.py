from html import escape

import requests
import threading
import webbrowser
from html import escape
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from spotipy.oauth2 import SpotifyOAuth

load_dotenv()
API = "https://api.spotify.com/v1"

# Nome exibido -> ID da playlist
PLAYLISTS = {
    "Holzier": "6VCjn7Ch6ptVcMTp1DuO48",
    "Noah Kahan": "1Q6TSnOVIWVmTA56oA4LSz",
    "Nemesis": "0X94pJkKmaNWyh8kRNdSk2",
}

auth = SpotifyOAuth(scope="user-modify-playback-state user-read-playback-state")
app = Flask(__name__)

PAGE = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Playlist Player</title>
<style>
  * { box-sizing: border-box; }
  :root {
    --bg: #1b2029;      /* superfície do cartão */
    --clara: #262d39;   /* "luz" do neumorfismo */
    --escura: #0f131a;  /* "sombra" do neumorfismo */
    --texto: #e8edf4;
    --suave: #8b97a8;
    --acento: #f0b44c;
  }
  body {
    margin: 0; min-height: 100vh; padding: 24px;
    display: flex; align-items: center; justify-content: center;
    background: #121212; color: var(--texto);
    font-family: "Segoe UI", Helvetica, Arial, sans-serif;
  }

  /* Fundo: capa desfocada + degradê */
  .fundo {
    position: fixed; inset: -40px; z-index: -2; background-color: #2f4f58;
    background-size: cover; background-position: center;
    filter: blur(30px) brightness(.8) saturate(1.2);
    will-change: transform;
  }
  .degrade {
    position: fixed; inset: 0; z-index: -1;
    background: linear-gradient(180deg, rgba(18,18,18,0) 0%, #121212 85%);
  }

  /* Cartão principal (horizontal) */
  .player {
    width: min(1000px, 100%); background: var(--bg); border-radius: 36px;
    padding: 44px; display: grid; grid-template-columns: 1fr 1fr;
    gap: 48px; align-items: center;
    box-shadow: 0 30px 80px rgba(0,0,0,.55);
  }
  @media (max-width: 820px) { .player { grid-template-columns: 1fr; padding: 28px; } }

  /* Disco de vinil + anel de progresso */
  .disco-area { position: relative; width: min(400px, 100%); aspect-ratio: 1; margin: 0 auto; }
  .anel { position: absolute; inset: 0; width: 100%; height: 100%; }
  .trilho { fill: none; stroke: var(--escura); stroke-width: 3; }
  .progresso {
    fill: none; stroke: var(--acento); stroke-width: 4; stroke-linecap: round;
    stroke-dasharray: 603.19; stroke-dashoffset: 603.19;
    transition: stroke-dashoffset .25s linear;
  }
  .vinil {
    position: absolute; inset: 7%; border-radius: 50%;
    background: repeating-radial-gradient(circle at center, #0d171c 0 2px, #1a2a31 3px 4px);
    box-shadow: 0 14px 30px rgba(0,0,0,.5);
    animation: girar 9s linear infinite; animation-play-state: paused;
  }
  .vinil.girando { animation-play-state: running; }
  .vinil::before {  /* reflexo do disco */
    content: ""; position: absolute; inset: 0; border-radius: 50%;
    background: conic-gradient(from 30deg, transparent 0 20%, rgba(255,255,255,.10) 28%,
      transparent 36% 70%, rgba(255,255,255,.08) 78%, transparent 86%);
  }
  .rotulo {
    position: absolute; inset: 31%; border-radius: 50%; background: #2a3340;
    background-size: cover; background-position: center;
    box-shadow: 0 0 0 6px #0c1317;
  }
  .rotulo::after {  /* furinho central */
    content: ""; position: absolute; width: 12%; height: 12%; border-radius: 50%;
    top: 44%; left: 44%; background: var(--bg); box-shadow: inset 1px 1px 3px rgba(0,0,0,.6);
  }
  @keyframes girar { to { transform: rotate(360deg); } }

  /* Lado direito */
  .etiqueta { font-size: 12px; letter-spacing: .18em; color: var(--suave); text-transform: uppercase; }
  .titulo { font-size: clamp(24px, 3.2vw, 34px); font-weight: 800; margin: 8px 0 4px; }
  .artista { color: var(--suave); font-size: 16px; }
  .tempos { color: var(--suave); font-size: 14px; margin-top: 10px; font-variant-numeric: tabular-nums; }

  .controles { display: flex; align-items: center; justify-content: center; gap: 22px; margin: 30px 0 24px; }
  .nm {
    border: none; background: var(--bg); color: var(--texto); border-radius: 50%;
    width: 58px; height: 58px; display: grid; place-items: center; cursor: pointer;
    box-shadow: 6px 6px 14px var(--escura), -6px -6px 14px var(--clara);
    transition: all .15s;
  }
  .nm:hover { transform: translateY(-1px); }
  .nm:active, .nm.ativo {
    box-shadow: inset 4px 4px 10px var(--escura), inset -4px -4px 10px var(--clara);
  }
  .nm.ativo { color: var(--acento); }
  .nm.grande { width: 78px; height: 78px; }
  .nm svg { width: 24px; height: 24px; fill: currentColor; }
  .nm.grande svg { width: 30px; height: 30px; }

  .linha-volume { display: flex; align-items: center; gap: 14px; color: var(--suave); }
  .linha-volume svg { width: 22px; height: 22px; fill: currentColor; flex: none; }
  input[type=range] {
    -webkit-appearance: none; appearance: none; flex: 1; height: 6px;
    border-radius: 6px; background: var(--escura); outline: none;
  }
  input[type=range]::-webkit-slider-thumb {
    -webkit-appearance: none; width: 20px; height: 20px; border-radius: 50%;
    background: var(--bg); cursor: pointer;
    box-shadow: 3px 3px 6px var(--escura), -3px -3px 6px var(--clara);
  }
  input[type=range]::-moz-range-thumb {
    width: 20px; height: 20px; border: none; border-radius: 50%;
    background: var(--bg); cursor: pointer;
    box-shadow: 3px 3px 6px var(--escura), -3px -3px 6px var(--clara);
  }

  .extras { display: flex; justify-content: center; gap: 22px; margin: 24px 0; }
  .playlists { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 8px; }
  .pill {
    border: none; background: var(--bg); color: var(--texto); cursor: pointer;
    padding: 12px 22px; border-radius: 500px; font-size: 15px; font-weight: 700;
    box-shadow: 5px 5px 12px var(--escura), -5px -5px 12px var(--clara);
    transition: all .15s;
  }
  .pill:hover { transform: translateY(-1px); }
  .pill.ativo {
    color: var(--acento);
    box-shadow: inset 3px 3px 8px var(--escura), inset -3px -3px 8px var(--clara);
  }
  .aviso { margin-top: 14px; color: #ff7b6e; font-size: 14px; min-height: 18px; }
</style>
</head>
<body>
  <div class="fundo" id="fundo"></div>
  <div class="degrade"></div>

  <main class="player">
    <!-- Esquerda: disco -->
    <section class="disco-area">
      <svg class="anel" viewBox="0 0 200 200">
        <circle class="trilho" cx="100" cy="100" r="96"/>
        <circle class="progresso" id="anel" cx="100" cy="100" r="96" transform="rotate(-90 100 100)"/>
      </svg>
      <div class="vinil" id="vinil"><div class="rotulo" id="rotulo"></div></div>
    </section>

    <!-- Direita: informações e controles -->
    <section>
      <div class="etiqueta">Tocando agora</div>
      <div class="titulo" id="titulo">Nada tocando</div>
      <div class="artista" id="artista">Escolha uma playlist abaixo</div>
      <div class="tempos"><span id="tAtual">0:00</span> / <span id="tTotal">0:00</span></div>

      <div class="controles">
        <button class="nm" id="btnAnterior" title="Anterior">
          <svg viewBox="0 0 24 24"><path d="M6 6h2v12H6zM9.5 12l8.5 6V6z"/></svg>
        </button>
        <button class="nm grande" id="btnPlay" title="Play/Pause"></button>
        <button class="nm" id="btnProxima" title="Próxima">
          <svg viewBox="0 0 24 24"><path d="M16 6h2v12h-2zM6 18l8.5-6L6 6z"/></svg>
        </button>
      </div>

      <div class="linha-volume">
        <svg viewBox="0 0 24 24"><path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02z"/></svg>
        <input type="range" id="volume" min="0" max="100" value="50">
      </div>

      <div class="extras">
        <button class="nm" id="btnShuffle" title="Aleatório">
          <svg viewBox="0 0 24 24"><path d="M10.59 9.17L5.41 4 4 5.41l5.17 5.17 1.42-1.41zM14.5 4l2.04 2.04L4 18.59 5.41 20 17.96 7.46 20 9.5V4h-5.5zm.33 9.41l-1.41 1.41 3.13 3.13L14.5 20H20v-5.5l-2.04 2.04-3.13-3.13z"/></svg>
        </button>
        <button class="nm" id="btnRepeat" title="Repetir">
          <svg viewBox="0 0 24 24"><path d="M7 7h10v3l4-4-4-4v3H5v6h2V7zm10 10H7v-3l-4 4 4 4v-3h12v-6h-2v4z"/></svg>
        </button>
      </div>

      <div class="etiqueta">Playlists</div>
      <div class="playlists">__BOTOES__</div>
      <div class="aviso" id="aviso"></div>
    </section>
  </main>

<script>
  const $ = (id) => document.getElementById(id);
  const CIRC = 603.19;  // circunferência do anel (2 * pi * 96)
  const ICONE_PLAY = '<svg viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>';
  const ICONE_PAUSE = '<svg viewBox="0 0 24 24"><path d="M6 5h4v14H6zM14 5h4v14h-4z"/></svg>';

  let estado = null;        // último estado vindo do servidor
  let ultimaLeitura = 0;    // momento em que recebemos esse estado
  let esperando = false;    // evita várias buscas ao fim da música

  const fmt = (ms) => {
    const s = Math.floor(ms / 1000);
    return Math.floor(s / 60) + ":" + String(s % 60).padStart(2, "0");
  };

  async function api(url, corpo) {
    const r = await fetch(url, {
      method: corpo ? "POST" : "GET",
      headers: {"Content-Type": "application/json"},
      body: corpo ? JSON.stringify(corpo) : undefined,
    });
    return r.json();
  }

  // Posição atual da música (estimada entre uma leitura e outra)
  function posAtual() {
    if (!estado) return 0;
    const pos = estado.progresso + (estado.tocando ? Date.now() - ultimaLeitura : 0);
    return Math.min(pos, estado.duracao);
  }

  function desenhar() {
    if (!estado) {
      $("titulo").textContent = "Nada tocando";
      $("artista").textContent = "Escolha uma playlist abaixo";
      $("rotulo").style.backgroundImage = "";
      $("fundo").style.backgroundImage = "";
      $("vinil").classList.remove("girando");
      $("btnPlay").innerHTML = ICONE_PLAY;
      return;
    }
    const capa = "url('" + estado.capa + "')";
    $("titulo").textContent = estado.titulo;
    $("artista").textContent = estado.artista;
    $("rotulo").style.backgroundImage = capa;
    $("fundo").style.backgroundImage = capa;
    $("vinil").classList.toggle("girando", estado.tocando);
    $("btnPlay").innerHTML = estado.tocando ? ICONE_PAUSE : ICONE_PLAY;
    $("btnShuffle").classList.toggle("ativo", estado.shuffle);
    $("btnRepeat").classList.toggle("ativo", estado.repeat);
    $("tTotal").textContent = fmt(estado.duracao);
    if (document.activeElement !== $("volume") && estado.volume !== null) {
      $("volume").value = estado.volume;
    }
  }

  async function atualizar() {
    const d = await api("/api/estado");
    estado = d.ativo ? d : null;
    ultimaLeitura = Date.now();
    desenhar();
  }

  async function controle(acao, valor) {
    await api("/api/controle", {acao: acao, valor: valor});
    setTimeout(atualizar, 600);
  }

  // Botões do player
  $("btnAnterior").onclick = () => controle("anterior");
  $("btnProxima").onclick = () => controle("proxima");
  $("btnPlay").onclick = () => {
    const tocando = estado && estado.tocando;
    if (estado) {  // atualiza a tela na hora, sem esperar o Spotify
      estado.progresso = posAtual();
      estado.tocando = !tocando;
      ultimaLeitura = Date.now();
      desenhar();
    }
    controle(tocando ? "pause" : "play");
  };
  $("btnShuffle").onclick = () => estado && controle("shuffle", !estado.shuffle);
  $("btnRepeat").onclick = () => estado && controle("repeat", !estado.repeat);
  $("volume").onchange = (e) => controle("volume", Number(e.target.value));

  // Botões de playlist
  document.querySelectorAll(".pill").forEach((b) => {
    b.addEventListener("click", async () => {
      document.querySelectorAll(".pill").forEach((x) => x.classList.remove("ativo"));
      b.classList.add("ativo");
      const r = await api("/api/playlist", {nome: b.dataset.nome});
      $("aviso").textContent = r.msg === "Tocando!" ? "" : r.msg;
      setTimeout(atualizar, 1500);
    });
  });

  // Anima o anel de progresso e o tempo a cada 250 ms
  setInterval(() => {
    if (!estado) {
      $("anel").style.strokeDashoffset = CIRC;
      $("tAtual").textContent = "0:00";
      return;
    }
    const pos = posAtual();
    if (pos >= estado.duracao && !esperando) {  // acabou: busca a próxima faixa
      esperando = true;
      setTimeout(async () => { await atualizar(); esperando = false; }, 1200);
    }
    $("tAtual").textContent = fmt(pos);
    $("anel").style.strokeDashoffset = CIRC * (1 - pos / estado.duracao);
  }, 250);

  atualizar();
  setInterval(atualizar, 4000);
</script>
</body>
</html>
"""


def headers():
    """Pega o token e monta o cabeçalho de autorização."""
    token = auth.get_access_token(as_dict=False)
    return {"Authorization": f"Bearer {token}"}


def spotify(metodo, rota, **params):
    """Faz uma chamada à API REST do Spotify."""
    return requests.request(
        metodo, f"{API}{rota}", headers=headers(), params=params or None, timeout=10
    )


def tocar(playlist_id):
    """Inicia a reprodução da playlist no dispositivo ativo."""
    r = requests.put(
        f"{API}/me/player/play",
        headers=headers(),
        json={"context_uri": f"spotify:playlist:{playlist_id}"},
        timeout=10,
    )
    if r.status_code == 404:
        return "Nenhum dispositivo ativo. Abra o Spotify e tente de novo."
    r.raise_for_status()
    return "Tocando!"


@app.get("/")
def index():
    """Monta a página com um botão para cada playlist."""
    botoes = "".join(
        f'<button class="pill" data-nome="{escape(nome)}">{escape(nome)}</button>'
        for nome in PLAYLISTS
    )
    return PAGE.replace("__BOTOES__", botoes)


@app.get("/api/estado")
def api_estado():
    """Devolve o que está tocando agora (música, progresso, volume, modos)."""
    r = spotify("GET", "/me/player")
    if r.status_code != 200:  # 204 = nenhum dispositivo/nada tocando
        return jsonify(ativo=False)
    d = r.json()
    item = d.get("item")
    if not item:
        return jsonify(ativo=False)
    return jsonify(
        ativo=True,
        titulo=item["name"],
        artista=", ".join(a["name"] for a in item["artists"]),
        capa=item["album"]["images"][0]["url"],
        tocando=d.get("is_playing", False),
        progresso=d.get("progress_ms", 0),
        duracao=item["duration_ms"],
        volume=(d.get("device") or {}).get("volume_percent"),
        shuffle=d.get("shuffle_state", False),
        repeat=d.get("repeat_state", "off") != "off",
    )


@app.post("/api/playlist")
def api_playlist():
    """Toca a playlist escolhida."""
    nome = request.get_json()["nome"]
    return jsonify(msg=tocar(PLAYLISTS[nome]))


@app.post("/api/controle")
def api_controle():
    """Recebe os comandos dos botões e repassa para o Spotify."""
    dados = request.get_json()
    acao, valor = dados["acao"], dados.get("valor")

    if acao == "anterior":
        r = spotify("POST", "/me/player/previous")
    elif acao == "proxima":
        r = spotify("POST", "/me/player/next")
    elif acao == "pause":
        r = spotify("PUT", "/me/player/pause")
    elif acao == "play":
        r = spotify("PUT", "/me/player/play")
    elif acao == "volume":
        r = spotify("PUT", "/me/player/volume", volume_percent=int(valor))
    elif acao == "shuffle":
        r = spotify("PUT", "/me/player/shuffle", state=str(bool(valor)).lower())
    elif acao == "repeat":
        r = spotify("PUT", "/me/player/repeat", state="context" if valor else "off")
    else:
        return jsonify(ok=False), 400
    return jsonify(ok=r.status_code < 300)


PORTA = 5001

if __name__ == "__main__":
    # Abre o navegador 1 segundo depois, dando tempo do servidor subir
    threading.Timer(1, lambda: webbrowser.open(f"http://127.0.0.1:{PORTA}")).start()
    app.run(port=PORTA)