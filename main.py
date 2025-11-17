import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import create_document, get_documents, db
from schemas import Product as ProductSchema

app = FastAPI(title="TopGames API", description="Backend per e-commerce TopGames")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ProductCreate(ProductSchema):
    pass


def product_to_public(doc: dict) -> dict:
    doc = {**doc}
    if "_id" in doc:
        doc["id"] = str(doc.pop("_id"))
    if "created_at" in doc:
        doc["created_at"] = str(doc["created_at"])
    if "updated_at" in doc:
        doc["updated_at"] = str(doc["updated_at"])
    return doc


@app.get("/")
def read_root():
    return {"message": "TopGames API attiva"}


@app.get("/api/hello")
def hello():
    return {"message": "Ciao da TopGames Backend!"}


@app.get("/test")
def test_database():
    """Test endpoint per verificare la connessione al database"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = getattr(db, "name", "✅ Connected")
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    return response


@app.get("/api/categories")
def get_categories():
    """Categorie principali del sito"""
    return [
        {"key": "carte", "label": "Carte Collezionabili", "image": "https://images.unsplash.com/photo-1593113598332-cd288d649433?q=80&w=1600&auto=format&fit=crop"},
        {"key": "gadget", "label": "Gadget", "image": "https://images.unsplash.com/photo-1526657782461-9fe13402a841?q=80&w=1600&auto=format&fit=crop"},
        {"key": "videogiochi", "label": "Videogiochi", "image": "https://images.unsplash.com/photo-1542751371-adc38448a05e?q=80&w=1600&auto=format&fit=crop"},
    ]


@app.get("/api/products")
def list_products(
    category: Optional[str] = Query(None, description="Filtra per categoria"),
    q: Optional[str] = Query(None, description="Testo libero"),
    limit: int = Query(12, ge=1, le=50)
):
    """Lista prodotti con filtri base"""
    if db is None:
        # Nessun DB: restituisce lista vuota per non rompere la UI
        return []

    filters = {}
    if category:
        filters["category"] = category
    if q:
        filters["$or"] = [
            {"title": {"$regex": q, "$options": "i"}},
            {"description": {"$regex": q, "$options": "i"}},
            {"tags": {"$elemMatch": {"$regex": q, "$options": "i"}}},
        ]

    docs = get_documents("product", filters, limit)
    return [product_to_public(d) for d in docs]


@app.post("/api/products", status_code=201)
def create_product(payload: ProductCreate):
    if db is None:
        raise HTTPException(status_code=500, detail="Database non disponibile")
    inserted_id = create_document("product", payload)
    return {"id": inserted_id}


@app.get("/api/featured")
def featured_products(limit: int = Query(8, ge=1, le=12)):
    # Strategia semplice: prodotti con tag 'featured' se presenti, altrimenti ultimi inseriti
    if db is None:
        return []
    # Tentativo 1: con tag featured
    found = list(db["product"].find({"tags": "featured"}).limit(limit))
    if len(found) < limit:
        # fallback: ultimi inseriti
        more = list(db["product"].find({}).sort("created_at", -1).limit(limit - len(found)))
        found.extend(more)
    return [product_to_public(d) for d in found[:limit]]


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
