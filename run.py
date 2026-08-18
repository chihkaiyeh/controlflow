from app import create_app

app = create_app()

if __name__ == "__main__":
    # host=0.0.0.0 讓內網其他電腦也能連；debug 僅開發用
    app.run(host="0.0.0.0", port=5000, debug=True)
