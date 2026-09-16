from app.database import Base, engine
import app.models  # noqa: F401  (registra os modelos no metadata)

if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    print("Banco de dados pronto — tabelas criadas!")
