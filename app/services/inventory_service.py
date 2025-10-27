from models.database import DatabaseManager, Inventory, Space, Element, Attribute, Image, Video
from datetime import datetime
import os
import cv2

class InventoryService:
    def __init__(self, db_path='/app/data/inventory.db'):
        self.db_manager = DatabaseManager(db_path)
        self.db_manager.create_tables()
        self.current_inventory_id = None
        self.current_space_id = None
        self.current_element_id = None
        
    def enter_inventory(self, name, description=None):
        session = self.db_manager.get_session()
        try:
            inventory = Inventory(name=name, description=description)
            session.add(inventory)
            session.commit()
            self.current_inventory_id = inventory.id
            return inventory
        finally:
            session.close()
    
    def get_inventories(self):
        session = self.db_manager.get_session()
        try:
            return session.query(Inventory).all()
        finally:
            session.close()
            
    # ============ SPACES ============    
    def enter_space(self, space_name, description=None):
        if not self.current_inventory_id:
            raise ValueError("Debe crear o seleccionar un inventario primero")
        
        session = self.db_manager.get_session()
        try:
            space = session.query(Space).filter_by(
                inventory_id=self.current_inventory_id,
                name=space_name
            ).first()
            
            if not space:
                space = Space(
                    inventory_id=self.current_inventory_id,
                    name=space_name,
                    description=description
                )
                session.add(space)
                session.commit()
            
            self.current_space_id = space.id
            self.current_element_id = None
            return space
        finally:
            session.close()
    
    def get_spaces(self, inventory_id=None):
        inv_id = inventory_id or self.current_inventory_id
        if not inv_id:
            raise ValueError("No hay inventario seleccionado")
        
        session = self.db_manager.get_session()
        try:
            return session.query(Space).filter_by(inventory_id=inv_id).all()
        finally:
            session.close()
            
    # ============ ELEMENTS ============    
    def enter_element(self, name, description=None, amount=1):
        if not self.current_espacio_id:
            raise ValueError("Debe ingresar a un espacio primero")
        
        session = self.db_manager.get_session()
        try:
            element = Element(
                space_id=self.current_space_id,
                name=name,
                description=description,
                amount=amount
            )
            session.add(element)
            session.commit()
            
            self.current_element_id = element.id
            return element
        finally:
            session.close()
    
    def get_elements(self, space_id=None):
        spac_id = space_id or self.current_space_id
        if not spac_id:
            raise ValueError("No hay espacio seleccionado")
        
        session = self.db_manager.get_session()
        try:
            return session.query(Element).filter_by(space_id=spac_id).all()
        finally:
            session.close()
            
    # ============ ATTRIBUTES ============    
    def enter_attribute(self, key, value):
        if not self.current_element_id:
            raise ValueError("Debe ingresar a un elemento primero")
          
        session = self.db_manager.get_session()
        try:
            attribute = Attribute(
                element_id=self.current_element_id,
                key=key,
                value=value
            )
            session.add(attribute)
            session.commit()
            return attribute
        finally:
            session.close()
    
    def get_attributes(self, element_id):
        elem_id = element_id or self.current_element_id
        if not elem_id:
            raise ValueError("No hay elemento seleccionado")
          
        session = self.db_manager.get_session()
        try:
            return session.query(Attribute).filter_by(element_id=elem_id).all()
        finally:
            session.close()
    
    # ============ IMAGES ============
    def save_image(self, frame, description=None, image_folder='images'):
        spac_id = self.current_space_id
        if not spac_id:
            raise ValueError("Debe ingresar a un espacio primero")
          
        elem_id = self.current_element_id
        if not elem_id:
            raise ValueError("Debe ingresar a un elemento primero")
        
        full_folder = os.path.join(image_folder, f"space_{spac_id}", f"element_{elem_id}")
        os.makedirs(full_folder, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        file_name = f"image_{timestamp}.jpg"
        path = os.path.join(full_folder, file_name)
        
        cv2.imwrite(path, frame)
        
        # Registrar en la base de datos
        session = self.db_manager.get_session()
        try:
            image = Image(
                space_id=self.current_space_id,
                element_id=self.current_element_id,
                path=path,
                description=description
            )
            session.add(image)
            session.commit()
            return image
        finally:
            session.close()
    
    def get_images(self, element_id=None):
        elem_id = element_id or self.current_element_id
        if not elem_id:
            raise ValueError("No hay elemento seleccionado")
        
        session = self.db_manager.get_session()
        try:
            return session.query(Image).filter_by(element_id=elem_id).all()
        finally:
            session.close()
            
    # ============ VIDEOS ============
    def save_video(self, video_data, description=None, video_folder='videos'):
        if not self.current_space_id:
            raise ValueError("Debe ingresar a un espacio primero")
        
        full_folder = os.path.join(video_folder, f"space_{self.current_space_id}")
        os.makedirs(full_folder, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        file_name = f"video_{timestamp}.mp4"
        path = os.path.join(full_folder, file_name)
        
        # Guardar video (dependiendo de cómo recibas el video_data)
        # Si es un archivo bytes, lo guardas directamente
        if isinstance(video_data, bytes):
            with open(path, 'wb') as f:
                f.write(video_data)
        # Si es una ruta de archivo temporal
        elif isinstance(video_data, str) and os.path.exists(video_data):
            import shutil
            shutil.move(video_data, path)
        else:
            raise ValueError("video_data debe ser bytes o una ruta de archivo válida")
        
        # Registrar en la base de datos
        session = self.db_manager.get_session()
        try:
            video = Video(
                space_id=self.current_space_id,
                path=path,
                description=description
            )
            session.add(video)
            session.commit()
            return video
        finally:
            session.close()
    
    def get_videos(self, space_id=None):
        spac_id = space_id or self.current_space_id
        if not spac_id:
            raise ValueError("No hay espacio seleccionado")
        
        session = self.db_manager.get_session()
        try:
            return session.query(Video).filter_by(space_id=spac_id).all()
        finally:
            session.close()
    
    # ============ SINCRONIZACIÓN ============
    def get_pending_sync(self):
        session = self.db_manager.get_session()
        try:
            pending = {
                'inventories': session.query(Inventory).filter_by(synced=False).all(),
                'spaces': session.query(Space).filter_by(synced=False).all(),
                'elements': session.query(Element).filter_by(synced=False).all(),
                'attributes': session.query(Attribute).filter_by(synced=False).all(),
                'images': session.query(Image).filter_by(synced=False).all(),
                'videos': session.query(Video).filter_by(synced=False).all()
            }
            return pending
        finally:
            session.close()
    
    def mark_as_synced(self, model, ids):
        """Marca registros como sincronizados"""
        session = self.db_manager.get_session()
        try:
            session.query(model).filter(model.id.in_(ids)).update(
                {'synced': True}, 
                synchronize_session=False
            )
            session.commit()
        finally:
            session.close()
    
    # ============ UTILS ============
    def get_current_status(self):
        return {
            'inventory_id': self.current_inventory_id,
            'space_id': self.current_space_id,
            'element_id': self.current_element_id
        }
        
    def reset_current_status(self):
        self.current_inventory_id = None
        self.current_space_id = None
        self.current_element_id = None