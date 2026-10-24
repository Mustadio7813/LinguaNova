"""Concrete SDXL implementation. Weights are local and verified beforehand."""
from PIL import Image
from ..models.model_compatibility import require_compatible
from ..image.image_reconstruction import preserve_outside


class DiffusersInpaintingAdapter:
    def restore(self,image,mask,model_directory,parameters,progress=None,cancelled=None):
        device=require_compatible(parameters)
        import torch
        from diffusers import AutoPipelineForInpainting
        dtype=torch.float16 if device=='cuda' else torch.float32
        pipeline=AutoPipelineForInpainting.from_pretrained(str(model_directory),torch_dtype=dtype,
                    variant='fp16',use_safetensors=True,local_files_only=True)
        try:
            pipeline.to(device)
            pipeline.enable_attention_slicing()
            if hasattr(pipeline,'enable_vae_tiling'):
                pipeline.enable_vae_tiling()
            def callback(pipe,step,timestep,callback_kwargs):
                if cancelled and cancelled.is_set():
                    raise RuntimeError('Inference cancelled')
                if progress: progress(step+1,int(parameters.get('steps',20)))
                return callback_kwargs
            # Aspect-preserving resize and padding; NEVER enlarge the effective
            # mask on the original canvas. Final composition copies only mask.
            original_size=image.size
            factor=min(1024/image.width,1024/image.height)
            size=(max(8,int(image.width*factor)//8*8),max(8,int(image.height*factor)//8*8))
            rgb=image.convert('RGB').resize(size,Image.Resampling.LANCZOS)
            local_mask=mask.convert('L').resize(size,Image.Resampling.NEAREST)
            seed=int(parameters.get('seed',0))
            generator=torch.Generator(device=device).manual_seed(seed)
            candidate=pipeline(prompt=parameters.get('background_prompt','Restore the continuous background texture, empty surface, no writing, no letters'),
                    negative_prompt='text, letters, words, watermark, symbols',image=rgb,mask_image=local_mask,
                    width=size[0],height=size[1],strength=.99,guidance_scale=7.0,
                    num_inference_steps=int(parameters.get('steps',20)),generator=generator,
                    callback_on_step_end=callback).images[0].resize(original_size,Image.Resampling.LANCZOS).convert('RGBA')
            candidate.putalpha(image.convert('RGBA').getchannel('A'))
            return preserve_outside(image,candidate,mask)
        finally:
            del pipeline
            if device=='cuda': torch.cuda.empty_cache()
