"""Start only the isolated local demo; no production environment is read."""
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8093, reload=False)
