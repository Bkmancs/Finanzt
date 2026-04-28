import sqlite3
import unicodedata
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes

TOKEN = "TU_TOKEN_AQUI"

# -----------------------
# NORMALIZAR TEXTO
# -----------------------
def normalizar(texto):
    texto = texto.lower().strip()
    texto = unicodedata.normalize('NFD', texto)
    texto = texto.encode('ascii', 'ignore').decode('utf-8')
    texto = texto.replace(" ", "_")
    return texto

# -----------------------
# BASE DE DATOS
# -----------------------
def init_db():
    conn = sqlite3.connect("finanzas.db")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS categorias (
        nombre TEXT PRIMARY KEY,
        tipo TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS movimientos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha TEXT,
        cantidad REAL,
        categoria TEXT,
        tipo TEXT
    )
    """)

    categorias = [
        ("ingreso", "ingreso"),
        ("ingreso_extra", "ingreso"),
        ("ingreso_excursion", "ingreso"),
        ("comida", "gasto"),
        ("combustible", "gasto"),
        ("seguro_auto", "gasto"),
        ("seguro_moto", "gasto"),
        ("seguro_salud", "gasto"),
        ("salidas", "gasto"),
        ("alquiler", "gasto"),
        ("servicios", "gasto")
    ]

    for nombre, tipo in categorias:
        try:
            cursor.execute("INSERT INTO categorias (nombre, tipo) VALUES (?, ?)", (nombre, tipo))
        except:
            pass

    conn.commit()
    conn.close()

# -----------------------
# VALIDAR CATEGORIA
# -----------------------
def obtener_tipo_categoria(categoria):
    conn = sqlite3.connect("finanzas.db")
    cursor = conn.cursor()

    cursor.execute("SELECT tipo FROM categorias WHERE nombre=?", (categoria,))
    resultado = cursor.fetchone()

    conn.close()
    return resultado[0] if resultado else None

# -----------------------
# GUARDAR MOVIMIENTO
# -----------------------
def guardar(cantidad, categoria):
    tipo = obtener_tipo_categoria(categoria)

    if not tipo:
        return False

    conn = sqlite3.connect("finanzas.db")
    cursor = conn.cursor()

    fecha = datetime.now().strftime("%Y-%m-%d")

    cursor.execute("""
        INSERT INTO movimientos (fecha, cantidad, categoria, tipo)
        VALUES (?, ?, ?, ?)
    """, (fecha, cantidad, categoria, tipo))

    conn.commit()
    conn.close()
    return True

# -----------------------
# TOTAL
# -----------------------
def obtener_total():
    conn = sqlite3.connect("finanzas.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT tipo, SUM(cantidad)
        FROM movimientos
        GROUP BY tipo
    """)

    datos = cursor.fetchall()
    conn.close()

    ingresos = 0
    gastos = 0

    for tipo, total in datos:
        if tipo == "ingreso":
            ingresos = total or 0
        else:
            gastos = total or 0

    return ingresos, gastos

# -----------------------
# RESUMEN POR CATEGORIA
# -----------------------
def resumen_categorias():
    conn = sqlite3.connect("finanzas.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT categoria, SUM(cantidad)
        FROM movimientos
        GROUP BY categoria
    """)

    datos = cursor.fetchall()
    conn.close()

    return datos

# -----------------------
# COMANDOS
# -----------------------
async def total(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ingresos, gastos = obtener_total()
    balance = ingresos - gastos

    mensaje = (
        f"💰 Ingresos: {ingresos}\n"
        f"💸 Gastos: {gastos}\n"
        f"📊 Balance: {balance}"
    )

    await update.message.reply_text(mensaje)

async def categorias_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    datos = resumen_categorias()

    if not datos:
        await update.message.reply_text("No hay datos aún.")
        return

    mensaje = "📊 Gastos por categoría:\n"
    for categoria, total in datos:
        mensaje += f"{categoria}: {total}\n"

    await update.message.reply_text(mensaje)

# -----------------------
# MENSAJES
# -----------------------
async def manejar_mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = normalizar(update.message.text)

    try:
        partes = texto.split("_")
        cantidad = float(partes[0])
        categoria = "_".join(partes[1:])

        if guardar(cantidad, categoria):
            await update.message.reply_text("✅ Guardado")
        else:
            await update.message.reply_text("❌ Categoría no válida")

    except:
        await update.message.reply_text(
            "Formato correcto:\n"
            "20 comida\n"
            "1500 ingreso\n"
            "30 seguro auto"
        )

# -----------------------
# MAIN
# -----------------------
def main():
    init_db()

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("total", total))
    app.add_handler(CommandHandler("categorias", categorias_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, manejar_mensaje))

    print("Bot funcionando...")
    app.run_polling()

if __name__ == "__main__":
    main()
