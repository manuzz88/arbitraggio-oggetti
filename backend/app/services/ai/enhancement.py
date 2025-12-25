import io
import asyncio
from pathlib import Path
from typing import List, Optional
from PIL import Image
from loguru import logger

from app.config import settings


class ImageEnhancer:
    """Migliora le immagini dei prodotti usando AI (Real-ESRGAN, RemBG)"""
    
    def __init__(self):
        self.realesrgan_model = None
        self.rembg_session = None
        self._initialized = False
    
    async def initialize(self):
        """Inizializza i modelli AI (lazy loading)"""
        if self._initialized:
            return
        
        try:
            # Import lazy per non bloccare se non installati
            logger.info("Initializing image enhancement models...")
            
            # Real-ESRGAN per upscaling
            try:
                from basicsr.archs.rrdbnet_arch import RRDBNet
                from realesrgan import RealESRGANer
                import torch
                
                model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=4)
                model_path = Path(settings.REAL_ESRGAN_MODEL_PATH) / "RealESRGAN_x4plus.pth"
                
                if model_path.exists():
                    self.realesrgan_model = RealESRGANer(
                        scale=4,
                        model_path=str(model_path),
                        model=model,
                        tile=0,
                        tile_pad=10,
                        pre_pad=0,
                        half=True if torch.cuda.is_available() else False,
                        gpu_id=0 if torch.cuda.is_available() else None
                    )
                    logger.info("Real-ESRGAN model loaded")
                else:
                    logger.warning(f"Real-ESRGAN model not found at {model_path}")
                    
            except ImportError:
                logger.warning("Real-ESRGAN not installed, upscaling disabled")
            
            # RemBG per rimozione sfondo
            try:
                from rembg import new_session
                self.rembg_session = new_session("u2net")
                logger.info("RemBG model loaded")
            except ImportError:
                logger.warning("RemBG not installed, background removal disabled")
            
            self._initialized = True
            
        except Exception as e:
            logger.error(f"Error initializing enhancement models: {e}")
    
    async def enhance_image(
        self,
        image_bytes: bytes,
        upscale: bool = True,
        remove_background: bool = False,
        target_size: Optional[tuple] = (1200, 1200)
    ) -> bytes:
        """
        Migliora una singola immagine
        
        Args:
            image_bytes: Immagine originale in bytes
            upscale: Se applicare upscaling AI
            remove_background: Se rimuovere lo sfondo
            target_size: Dimensione target finale (width, height)
        
        Returns:
            Immagine migliorata in bytes (JPEG)
        """
        await self.initialize()
        
        # Carica immagine
        img = Image.open(io.BytesIO(image_bytes))
        
        # Converti in RGB se necessario
        if img.mode != "RGB":
            img = img.convert("RGB")
        
        # 1. Rimozione sfondo (opzionale)
        if remove_background and self.rembg_session:
            img = await self._remove_background(img)
        
        # 2. Upscaling AI
        if upscale and self.realesrgan_model:
            img = await self._upscale(img)
        
        # 3. Resize a dimensione target
        if target_size:
            img = self._smart_resize(img, target_size)
        
        # 4. Ottimizza qualità
        img = self._optimize_quality(img)
        
        # Converti in bytes
        output = io.BytesIO()
        img.save(output, format="JPEG", quality=90, optimize=True)
        return output.getvalue()
    
    async def enhance_images(
        self,
        images: List[bytes],
        upscale: bool = True,
        remove_background: bool = False
    ) -> List[bytes]:
        """Migliora multiple immagini"""
        enhanced = []
        
        for i, img_bytes in enumerate(images):
            try:
                logger.info(f"Enhancing image {i+1}/{len(images)}")
                enhanced_img = await self.enhance_image(
                    img_bytes,
                    upscale=upscale,
                    remove_background=remove_background
                )
                enhanced.append(enhanced_img)
            except Exception as e:
                logger.error(f"Error enhancing image {i+1}: {e}")
                # Mantieni originale se fallisce
                enhanced.append(img_bytes)
        
        return enhanced
    
    async def _remove_background(self, img: Image.Image) -> Image.Image:
        """Rimuove lo sfondo usando RemBG"""
        try:
            from rembg import remove
            
            # Esegui in thread separato per non bloccare
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: remove(img, session=self.rembg_session)
            )
            
            # Aggiungi sfondo bianco
            if result.mode == "RGBA":
                background = Image.new("RGB", result.size, (255, 255, 255))
                background.paste(result, mask=result.split()[3])
                return background
            
            return result
            
        except Exception as e:
            logger.error(f"Background removal failed: {e}")
            return img
    
    async def _upscale(self, img: Image.Image) -> Image.Image:
        """Upscale immagine con Real-ESRGAN"""
        try:
            import numpy as np
            import cv2
            
            # Converti PIL -> numpy
            img_np = np.array(img)
            img_np = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
            
            # Esegui upscaling
            loop = asyncio.get_event_loop()
            output, _ = await loop.run_in_executor(
                None,
                lambda: self.realesrgan_model.enhance(img_np, outscale=2)
            )
            
            # Converti numpy -> PIL
            output = cv2.cvtColor(output, cv2.COLOR_BGR2RGB)
            return Image.fromarray(output)
            
        except Exception as e:
            logger.error(f"Upscaling failed: {e}")
            return img
    
    def _smart_resize(self, img: Image.Image, target_size: tuple) -> Image.Image:
        """Resize mantenendo aspect ratio"""
        img.thumbnail(target_size, Image.Resampling.LANCZOS)
        return img
    
    def _optimize_quality(self, img: Image.Image) -> Image.Image:
        """Ottimizza qualità immagine"""
        # Aumenta leggermente contrasto e saturazione
        from PIL import ImageEnhance
        
        # Contrasto
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.05)
        
        # Saturazione
        enhancer = ImageEnhance.Color(img)
        img = enhancer.enhance(1.05)
        
        # Sharpness
        enhancer = ImageEnhance.Sharpness(img)
        img = enhancer.enhance(1.1)
        
        return img
