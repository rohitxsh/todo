from fastapi import FastAPI, Depends, Request, Response, HTTPException
from sqlalchemy.orm import Session
from time import time
from uuid import uuid4
import logging, uvicorn
import app.models as models
from app.database import engine, SessionLocal

# create the SQLite DB on app initialization
models.Base.metadata.create_all(bind=engine)

# app = FastAPI(debug=True)
app = FastAPI()

# setup logger
logging.basicConfig(filename="log.txt", level=logging.DEBUG, format='%(asctime)s %(levelname)s %(module)s %(name)s %(message)s')
logger = logging.getLogger(__name__)
# log all requests
@app.middleware("http")
async def log_requests(request: Request, call_next) -> Response:
    request.state.id = str(uuid4())

    start_time = time()
    response = await call_next(request)
    end_time = (time() - start_time) * 1000

    logger.info(f"{request.state.id} {request.url.path}{f'?{str(request.query_params)}' if request.query_params else ''} Time={'{0:.2f}'.format(end_time)} ms status_code={response.status_code}")

    response.headers['X-Correlation-ID'] = request.state.id
    return response
# custom method to log errors in a defined format
def log_error(err: str, request: Request) -> None:
    logger.error(f"{request.state.id} {request.url.path}{f'?{str(request.query_params)}' if request.query_params else ''} err=\"{err}\"")

# DB dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/",
         responses={
             200: {
                 "content": {
                     "application/json": {
                         "example": []
                        }
                    },
                },
            },
        )
def get_todos(request: Request, db: Session = Depends(get_db)):
    try:
        return db.query(models.Todo).all()
    except Exception as err:
        log_error(str(err), request)
        raise HTTPException(status_code=500) from err

@app.post("/add")
def add(request: Request, task: str, db: Session = Depends(get_db)):
    try:
        todo = models.Todo(task=task)
        db.add(todo)
        db.commit()
        return {"message": "Successfully added the new ToDo"}
    except Exception as err:
        log_error(str(err), request)
        raise HTTPException(status_code=500) from err

@app.get("/edit",
         responses={
             200: {
                 "content": {
                     "application/json": {
                         "example": {
                             "message": "Successfully edited 1"
                         }
                        }
                    },
                },
             404: {
                 "content": {
                     "application/json": {
                         "example": "ToDo ID not found!"
                        }
                    },
                },
            },
        )
def edit(request: Request, todo_id: int, task: str, completed: bool = False, db: Session = Depends(get_db)):
    try:
        todo = db.query(models.Todo).filter(models.Todo.id == todo_id).first()

        if not todo:
            return HTTPException(status_code=404, detail="ToDo ID not found!")

        todo.task = task
        todo.completed = completed
        db.commit()
        return {"message": f"Successfully edited {todo_id}"}
    except Exception as err:
        log_error(str(err), request)
        raise HTTPException(status_code=500) from err

@app.get("/delete",
         responses={
             200: {
                 "content": {
                     "application/json": {
                         "example": {
                             "message": "Successfully deleted 1"
                         }
                        }
                    },
                },
             404: {
                 "content": {
                     "application/json": {
                         "example": "ToDo ID not found!"
                        }
                    },
                },
            },
        )
def delete(request: Request, todo_id: int, db: Session = Depends(get_db)):
    try:
        todo = db.query(models.Todo).filter(models.Todo.id == todo_id).first()
        db.delete(todo)
        db.commit()
        return {"message": f"Successfully deleted {todo_id}"}
    except Exception as err:
        log_error(str(err), request)
        if "NoneType" in str(err):
            raise HTTPException(status_code=404, detail="ToDo ID not found!") from err
        raise HTTPException(status_code=500) from err

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)