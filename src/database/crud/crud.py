# crud_helper.py
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from contextlib import contextmanager
from typing import Dict, Optional, List, Any
from datetime import datetime

from ..models import models
from src.utils.logging_config import get_logger

logger = get_logger(module_name="crud", DIR="crud")


class DatabaseError(Exception):
    """Excepción base para errores de base de datos"""
    pass


class UserNotFoundError(DatabaseError):
    """Excepción cuando no se encuentra un usuario"""
    pass


class ChatNotFoundError(DatabaseError):
    """Excepción cuando no se encuentra un chat"""
    pass


class CrudHelper:
    def __init__(self, db_host: str, db_pass: str, db_user: str, db_name: str, db_port: str):
        """
        Inicializa el helper de base de datos de la aplicacion
        
        Args:
            db_host: Host de la base de datos
            db_pass: Contraseña de la base de datos
            db_user: Usuario de la base de datos
            db_name: Nombre de la base de datos
            db_port: Puerto de la base de datos
        """
        self.database_url = f"postgresql+psycopg2://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
        self.engine = create_engine(
            self.database_url,
            pool_pre_ping=True,  # Verifica conexiones antes de usarlas
            pool_recycle=3600,   # Recicla conexiones cada hora
            echo=False           # No mostrar queries en producción
        )
        
    @contextmanager
    def session_scope(self):
        """
        Context manager para manejar sesiones de base de datos de forma segura
        """
        Session = sessionmaker(bind=self.engine)
        session = Session()
        try:
            yield session
            session.commit()
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error en operación de base de datos: {str(e)}")
            raise DatabaseError(f"Error en base de datos: {str(e)}") from e
        except Exception as e:
            session.rollback()
            logger.error(f"Error inesperado: {str(e)}")
            raise
        finally:
            session.close()

    def create_database(self) -> None:
        """
        Crea todas las tablas en la base de datos
        """
        try:
            models.Base.metadata.create_all(self.engine)
            logger.info("Base de datos creada/verificada exitosamente")
        except SQLAlchemyError as e:
            logger.error(f"Error al crear base de datos: {str(e)}")
            raise DatabaseError(f"No se pudo crear la base de datos: {str(e)}") from e

    def post_new_user(self, name: str, db_credentials: Dict) -> Dict[str, Any]:
        """
        Crea un nuevo usuario y su chat asociado
        
        Args:
            name: Nombre del usuario
            db_credentials: Credenciales de base de datos del usuario
            
        Returns:
            Dict con información del usuario y chat creados
            
        Raises:
            DatabaseError: Si ocurre un error en la operación
        """
        if not name or not isinstance(name, str):
            raise ValueError("El nombre debe ser un string no vacío")
        if not db_credentials or not isinstance(db_credentials, dict):
            raise ValueError("Las credenciales deben ser un diccionario no vacío")

        with self.session_scope() as session:
            try:
                # Crear usuario
                user_db = models.UserModel(
                    name=name.strip(),
                    db_credentials=db_credentials
                )
                session.add(user_db)
                session.flush()  # Para obtener el ID

                # Crear chat asociado
                chat_db = models.ChatModel(user_id=user_db.user_id)
                session.add(chat_db)
                session.flush()  # Para obtener el ID del chat

                logger.info(f"Usuario creado: ID={user_db.user_id}, Nombre={name}")
                
                return {
                    "user_id": user_db.user_id,
                    "chat_id": chat_db.chat_id,
                    "name": user_db.name,
                    "created_at": datetime.now().isoformat()
                }

            except IntegrityError as e:
                logger.error(f"Error de integridad al crear usuario: {str(e)}")
                raise DatabaseError("El usuario ya existe o hay conflictos de datos") from e


    def put_db_credentials(self, user_id: int, new_db_credentials: Dict) -> Dict[str, Any]:
        """
        Actualiza las credenciales de base de datos de un usuario específico
        
        Args:
            user_id: ID del usuario a actualizar
            new_db_credentials: Nuevo diccionario con las credenciales
            
        Returns:
            Dict con la información actualizada del usuario
            
        Raises:
            UserNotFoundError: Si no se encuentra el usuario
            ValueError: Si las credenciales son inválidas
            DatabaseError: Si ocurre un error en la operación
        """
        if not new_db_credentials or not isinstance(new_db_credentials, dict):
            raise ValueError("Las nuevas credenciales deben ser un diccionario no vacío")

        with self.session_scope() as session:
            user = session.query(models.UserModel).filter_by(user_id=user_id).first()
            
            if not user:
                logger.warning(f"Intento de actualizar usuario inexistente: {user_id}")
                raise UserNotFoundError(f"Usuario con ID {user_id} no encontrado")

            # Validar estructura mínima de credenciales (personalizar según necesidades)
            # required_fields = ['host', 'port', 'database', 'user']  # Ejemplo
            # missing_fields = [field for field in required_fields if field not in new_db_credentials]
            # if missing_fields:
            #     raise ValueError(f"Credenciales incompletas. Faltan: {missing_fields}")

            old_credentials = user.db_credentials
            user.db_credentials = new_db_credentials
            
            logger.info(f"Credenciales actualizadas para usuario {user_id}")
            logger.debug(f"Credenciales anteriores: {old_credentials}")
            
            return {
                "user_id": user.user_id,
                "name": user.name,
                "db_credentials": user.db_credentials,
                "updated_at": datetime.now().isoformat()
            }
        
    
    def post_new_chat_id(self, user_id):
        if not user_id or not isinstance(user_id, int):
            raise ValueError(f"EL nuevo chat id tiene un user_id no valido: {user_id}")
        
        with self.session_scope() as session:
            chat_db = models.ChatModel(user_id=user_id)
            session.add(chat_db)
            session.flush()
        
        return {'new_chat_id':chat_db.chat_id, 'user_id':user_id}
        
        

if __name__=="__main__":
    from src.utils import settings
    crud_helper = CrudHelper(db_host=settings.DB_HOST, db_name=settings.DB_NAME, db_pass=settings.DB_PASS, db_port=settings.DB_PORT, db_user=settings.DB_USER)

    # Construir la db
    crud_helper.create_database()

    # 
    # crud_helper.post_new_user(name="thomas", db_credentials={'a':1})

    # crud_helper.post_new_chat_id(user_id=1)





  
        

"""
python3 -m src.database.crud.crud

"""