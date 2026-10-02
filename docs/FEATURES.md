# Dokumentasi Fitur chat-api

Service FastAPI mandiri untuk riwayat chat dan balasan asisten eSIM
(RoaminRabbit). Data disimpan di Postgres, balasan dibuat oleh model lokal.

## Daftar fitur

| Fitur | Endpoint | Auth | Keterangan |
|---|---|---|---|
| Health check | `GET /health` | tidak perlu | Cek service hidup. Mengembalikan `{"status": "ok"}`. |
| Ambil riwayat chat (`getChatList`) | `GET /chat/{session_id}/list` | `X-API-Key` | Semua turn dalam satu sesi, urut sesuai kedatangan. |
| Simpan satu turn | `POST /chat/{session_id}/messages` | `X-API-Key` | Menyimpan object pesan apa adanya. Hanya `role` (`assistant` atau `user`) yang divalidasi. |
| Balas teks bebas | `POST /chat/{session_id}/reply` | `X-API-Key` | Body `{"text": "..."}`. Menyimpan pesan user, memanggil model, menyimpan dan mengembalikan balasan. |
| Kirim chip (`sendChat`) | `POST /chat/{session_id}/send` | `X-API-Key` | Body `{"message", "chip", "arg"}`. Balasan dikembalikan datar (satu object), bukan list. |

### Format respons

- `/list` dan `/reply`: `{"status": "success", "data": {"messages": [...]}}`
- `/send`: `{"status": "success", "data": <assistantMessage>}`

### Autentikasi

Satu shared secret di `API_KEY` (file `.env`). Semua `/chat/*` wajib mengirim
header `X-API-Key`. Key salah atau tidak ada menghasilkan `401`. `/health`
tidak butuh key. Ini gate untuk pengembangan lokal, bukan auth per user.

### Penyimpanan

Tabel `chat_messages`: `session_id`, `sequence` (urutan 1-based per sesi),
`role`, `payload` (JSONB, pesan lengkap apa adanya), `created_at`. Pasangan
`(session_id, sequence)` unik.

### Format pesan asisten

Model diminta menjawab dengan satu object JSON: `role`, `text`, `chip`,
`chips[]`, dan opsional `isPopup`, `requiresLogin`, `deeplink`.

- Nilai `chip` yang valid: `destinations`, `usage`, `plan_choice`,
  `region_choice`, `cta_plan`, `esim_choice`, `device`, `ios_error`,
  `android_error`, `troubleshoot_check`, `fix_applied`, `nav_compatibility`,
  `nav_destinations`, `nav_install_guide`, `nav_signin`, `whatsapp_only`, `none`.
- Setiap `chips[].arg` selalu berupa object yang memuat `packageId`,
  `countryId`, `orderId`, `esimId` (diisi `""` bila tidak berlaku). Bila model
  mengirim string atau mengosongkannya, service menormalkannya otomatis.
- Output yang bukan JSON valid, atau memakai `chip` di luar daftar, ditolak
  dan dicoba ulang (lihat di bawah).

## Model yang digunakan dan urutan switching

Model dipanggil lewat endpoint OpenAI-compatible `/chat/completions`.
Urutan dicoba dari model terbesar ke terkecil, lalu pesan statis.

| Urutan | Model | Server | Variabel `.env` | Perkiraan ukuran |
|---|---|---|---|---|
| 1 (primary) | `google/gemma-4-e4b` | LM Studio, `http://localhost:1234/v1` | `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL` | ~4B parameter efektif (dari nama `e4b`) |
| 2 (backup) | `llama3.2` | Ollama, `http://localhost:11434/v1` | `LLM_FALLBACK_BASE_URL`, `LLM_FALLBACK_API_KEY`, `LLM_FALLBACK_MODEL` | 3.2B (terukur di Ollama) |
| 3 (backup kedua) | `llama3.2:1b` | Ollama, `http://localhost:11434/v1` | `LLM_FALLBACK2_BASE_URL`, `LLM_FALLBACK2_API_KEY`, `LLM_FALLBACK2_MODEL` | ~1B |
| 4 (terakhir) | pesan statis `whatsapp_only` | tanpa model | - | - |

Ukuran `gemma-4-e4b` dan `llama3.2:1b` adalah perkiraan dari nama model,
bukan hasil pengukuran. Cek di LM Studio dan `ollama list`. Model `llama3.2:1b`
harus di-pull dulu: `ollama pull llama3.2:1b`.

### Alur switching (`app/llm_client.py`)

```
request /reply atau /send
   |
   v
[1] LM Studio: google/gemma-4-e4b
      percobaan 1 -> gagal? -> percobaan 2 (+ pesan koreksi "balas HANYA JSON")
   |  kedua percobaan gagal
   v
[2] Ollama: llama3.2
      percobaan 1 -> gagal? -> percobaan 2 (+ pesan koreksi)
   |  kedua percobaan gagal
   v
[3] Ollama: llama3.2:1b
      percobaan 1 -> gagal? -> percobaan 2 (+ pesan koreksi)
   |  kedua percobaan gagal
   v
[4] Pesan statis whatsapp_only (arahkan user ke WhatsApp)
```

- Tiap model dicoba maksimal 2 kali. Percobaan kedua menambahkan pesan koreksi
  agar model menjawab JSON saja.
- Dianggap gagal bila: server tidak terjangkau, timeout (`LLM_TIMEOUT_S`,
  default 30 detik), respons bukan JSON, `chip` tidak dikenal, atau `text` kosong.
- Ini urutan ketat dari model terbesar ke terkecil, bukan load balancing. Model
  berikutnya hanya dipanggil bila model sebelumnya gagal dua kali.
- `generate_reply` tidak pernah melempar error. Bila semua model gagal, endpoint
  tetap membalas `200` dengan pesan `whatsapp_only` (WhatsApp +62 813-6873-703),
  bukan `5xx`.
- Kegagalan tiap tahap dicetak ke log (`[llm_client] tier N (...) failed`).

### Mengganti model

Ubah `.env`, lalu restart server:

```bash
LLM_MODEL=google/gemma-4-e4b
LLM_FALLBACK_MODEL=llama3.2
LLM_FALLBACK2_MODEL=llama3.2:1b
```

Agar urutan tetap "besar ke kecil", isi `LLM_MODEL` dengan model yang lebih
besar dari `LLM_FALLBACK_MODEL`, dan seterusnya. Daftar tingkat ada di
`_provider_chain()` di `app/llm_client.py`.

## Konfigurasi

| Variabel | Default | Keterangan |
|---|---|---|
| `API_KEY` | wajib, tanpa default | Aplikasi gagal start bila kosong. |
| `DATABASE_URL` | `postgresql+psycopg2://postgres:postgres@localhost:5432/chat_api` | Postgres. |
| `LLM_BASE_URL` / `LLM_API_KEY` / `LLM_MODEL` | LM Studio `:1234`, `lm-studio`, `google/gemma-4-e4b` | Model primary. |
| `LLM_FALLBACK_BASE_URL` / `LLM_FALLBACK_API_KEY` / `LLM_FALLBACK_MODEL` | Ollama `:11434`, `ollama`, `llama3.2` | Model backup. |
| `LLM_FALLBACK2_BASE_URL` / `LLM_FALLBACK2_API_KEY` / `LLM_FALLBACK2_MODEL` | Ollama `:11434`, `ollama`, `llama3.2:1b` | Model backup kedua (terkecil). |
| `LLM_TIMEOUT_S` | `30.0` | Batas waktu per panggilan model. |
| `CORS_ORIGINS` | `["*"]` | Origin yang diizinkan. Batasi sebelum produksi. |

## Batasan

- Tidak ada katalog produk asli. `DEMO_CATALOG` di `app/llm_client.py` hanya
  contoh agar id dan isoCode konsisten dengan `scripts/seed_demo.py`.
- Tidak ada sistem order. `orderId` selalu `""`.
- `/messages` hanya menyimpan dan memutar ulang turn, tanpa dialogue engine.
- Watchdog (`scripts/watchdog.sh`) tidak bertahan setelah reboot.
