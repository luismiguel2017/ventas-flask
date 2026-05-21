import psycopg2

def test_connection():
    try:
        conn = psycopg2.connect(
            host="localhost",
            port="5432",
            database="Ventas",
            user="postgres",
            password="luis1988",
            options='-c client_encoding=UTF8'  # fuerza UTF-8
        )
        cursor = conn.cursor()
        cursor.execute("SELECT 1;")
        result = cursor.fetchone()
        print("✅ Conexión exitosa. Resultado:", result)
        cursor.close()
        conn.close()
    except Exception as e:
        print("❌ Error de conexión:", e)

if __name__ == "__main__":
    test_connection()
