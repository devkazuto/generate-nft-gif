import os
import json
import random
import hashlib
from datetime import datetime
from PIL import Image, ImageSequence

class CharacterGenerator:
    def __init__(self, config_path='config.json'):
        """
        Initialize the Character Generator with configuration
        
        Parameters:
        - config_path: Path to the configuration JSON file
        """
        # Load configuration
        with open(config_path, 'r') as config_file:
            self.config = json.load(config_file)
        
        # Set up directories
        self.base_dir = self.config.get('base_layers_directory', 'nft_layers')
        self.output_dir = self.config.get('output_directory', 'output')
        
        # Create output directories
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(os.path.join(self.output_dir, 'images'), exist_ok=True)
        os.makedirs(os.path.join(self.output_dir, 'json'), exist_ok=True)
        
        # Track generated DNAs
        self.generated_dnas = set()
    
    def _generate_dna_hash(self, layers):
        """
        Generate a unique DNA hash for the selected layers
        
        Parameters:
        - layers: Dictionary of selected layer files
        
        Returns:
        - Unique DNA hash string
        """
        dna_string = '|'.join([f"{k}:{v['path']}" for k, v in layers.items()])
        return hashlib.sha1(dna_string.encode()).hexdigest()
    
    def _select_layer_file(self, layer_name):
        """
        Randomly select a file from a layer directory
        
        Parameters:
        - layer_name: Name of the layer
        
        Returns:
        - Dictionary with file path, type, and filename
        """
        layer_dir = os.path.join(self.base_dir, layer_name)
        if not os.path.exists(layer_dir):
            return None
        
        layer_files = [f for f in os.listdir(layer_dir) if f.lower().endswith(('.png', '.gif'))]
        
        if not layer_files:
            return None
        
        selected_file = random.choice(layer_files)
        file_path = os.path.join(layer_dir, selected_file)
        file_type = os.path.splitext(selected_file)[1].lower()[1:]
        
        return {
            'path': file_path,
            'type': file_type,
            'filename': selected_file
        }
    
    def generate_character(self, layers_order, edition, max_attempts=500):
        """
        Generate a unique character with metadata
        
        Parameters:
        - layers_order: List of layer names to include
        - edition: Character edition number
        - max_attempts: Maximum attempts to generate a unique character
        
        Returns:
        - Dictionary containing character metadata
        """
        for attempt in range(max_attempts):
            # Select layers
            selected_layers = {}
            for layer in layers_order:
                layer_file = self._select_layer_file(layer)
                if layer_file:
                    selected_layers[layer] = layer_file
            
            # Generate DNA
            dna = self._generate_dna_hash(selected_layers)
            
            # Check for uniqueness
            if dna not in self.generated_dnas:
                self.generated_dnas.add(dna)
                
                # Determine output type based on background
                background = selected_layers.get('Background')
                image_path = (
                    self._generate_gif_character(selected_layers, edition) 
                    if background and background['type'] == 'gif' 
                    else self._generate_png_character(selected_layers, edition)
                )
                
                # Prepare metadata
                metadata = {
                    "name": f"{self.config['collection_name']} #{edition}",
                    "description": self.config['collection_description'],
                    "image": f"{self.config['ipfs_base_uri']}{edition}.{image_path.split('.')[-1]}",
                    "dna": dna,
                    "edition": edition,
                    "date": int(datetime.now().timestamp() * 1000),
                    "attributes": [
                        {
                            "trait_type": layer,
                            "value": os.path.splitext(selected_layers[layer]['filename'])[0]
                        }
                        for layer in layers_order if layer in selected_layers
                    ],
                    "compiler": self.config['compiler']
                }
                
                # Save metadata JSON
                metadata_path = os.path.join(
                    self.output_dir, 
                    'json', 
                    f"{edition}.json"
                )
                with open(metadata_path, 'w') as f:
                    json.dump(metadata, f, indent=2)
                
                return metadata
        
        raise ValueError(f"Could not generate a unique character after {max_attempts} attempts")
    
    def _generate_png_character(self, selected_layers, edition):
        """
        Generate a PNG character
        
        Parameters:
        - selected_layers: Dictionary of selected layer files
        - edition: Character edition number
        
        Returns:
        - Path to generated PNG
        """
        # Load background (PNG)
        background = selected_layers.get('Background')
        background_image = Image.open(background['path']).convert("RGBA")
        
        # Create a new image with the same size and mode as background
        combined_image = Image.new("RGBA", background_image.size, (0, 0, 0, 0))
        
        # Paste background first
        combined_image.paste(background_image, (0, 0))
        
        # Paste other static layers
        for layer_name, layer_info in selected_layers.items():
            if layer_name == 'Background' or layer_info['type'] == 'gif':
                continue
            
            layer_image = Image.open(layer_info['path']).convert("RGBA")
            combined_image.paste(layer_image, (0, 0), layer_image)
        
        # Generate output path
        output_path = os.path.join(
            self.output_dir, 
            'images', 
            f"{edition}.png"
        )
        
        # Save the combined image
        combined_image.save(output_path)
        
        print(f"Generated character PNG: {output_path}")
        return output_path
    
    def _generate_gif_character(self, selected_layers, edition):
        """
        Generate a GIF character
        
        Parameters:
        - selected_layers: Dictionary of selected layer files
        - edition: Character edition number
        
        Returns:
        - Path to generated GIF
        """
        # Load background GIF
        background = selected_layers.get('Background')
        background_gif = Image.open(background['path'])
        
        # Prepare static layers
        static_layers = {}
        for layer_name, layer_info in selected_layers.items():
            if layer_name == 'Background' or layer_info['type'] == 'gif':
                continue
            
            layer_image = Image.open(layer_info['path']).convert("RGBA")
            static_layers[layer_name] = layer_image
        
        # Prepare frames
        frames = []
        for frame in ImageSequence.Iterator(background_gif):
            # Convert background frame to RGBA
            frame = frame.convert("RGBA")
            
            # Create a new image with the same size and mode as background frame
            combined_frame = Image.new("RGBA", frame.size, (0, 0, 0, 0))
            
            # Paste background frame first
            combined_frame.paste(frame, (0, 0))
            
            # Paste static layers
            for layer_image in static_layers.values():
                combined_frame.paste(layer_image, (0, 0), layer_image)
            
            frames.append(combined_frame)
        
        # Generate output path
        output_path = os.path.join(
            self.output_dir, 
            'images', 
            f"{edition}.gif"
        )
        
        # Save the combined GIF
        frames[0].save(
            output_path, 
            save_all=True, 
            append_images=frames[1:], 
            optimize=False, 
            duration=background_gif.info.get('duration', 100),  
            loop=0
        )
        
        print(f"Generated character GIF: {output_path}")
        return output_path
    
    def generate_collection(self):
        """
        Generate entire NFT collection based on configuration
        
        Returns:
        - List of generated character metadata
        """
        layers_order = self.config.get('layers_order', [])
        total_characters = self.config['generation_settings']['total_characters']
        max_attempts = self.config['generation_settings']['max_generation_attempts']
        
        generated_characters = []
        
        for edition in range(1, total_characters + 1):
            try:
                character_metadata = self.generate_character(
                    layers_order, 
                    edition, 
                    max_attempts
                )
                generated_characters.append(character_metadata)
                print(f"Generated character #{edition}")
            except ValueError as e:
                print(f"Error generating character #{edition}: {e}")
                break
        
        return generated_characters

def main():
    # Create generator with config
    generator = CharacterGenerator('config.json')
    
    # Generate entire collection
    generator.generate_collection()

if __name__ == "__main__":
    main()