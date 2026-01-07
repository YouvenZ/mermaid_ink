#!/usr/bin/env python3
"""
Inkscape extension to generate and insert Mermaid diagrams.
"""
import inkex
import os
import subprocess
import tempfile
import shutil

class MermaidGenerator(inkex.EffectExtension):
    """Extension to generate Mermaid diagrams."""
    
    def add_arguments(self, pars):
        pars.add_argument("--tab", type=str, default="diagram", help="Active tab")
        
        # Diagram parameters
        pars.add_argument("--mermaid_code", type=str, default="", help="Mermaid code")
        pars.add_argument("--mermaid_file", type=str, default="", help="Mermaid file path")
        pars.add_argument("--use_file", type=inkex.Boolean, default=False, help="Use external file")
        
        # Style parameters
        pars.add_argument("--theme", type=str, default="default", help="Mermaid theme")
        pars.add_argument("--background", type=str, default="white", help="Background color")
        pars.add_argument("--width", type=int, default=800, help="Width")
        pars.add_argument("--height", type=int, default=600, help="Height")
        
        # Format parameters
        pars.add_argument("--output_format", type=str, default="svg", help="Output format")
        pars.add_argument("--scale_factor", type=float, default=1.0, help="Scale factor")
        pars.add_argument("--quality", type=int, default=2, help="Quality level")
        pars.add_argument("--embed_image", type=inkex.Boolean, default=True, help="Embed image")
        
        # Placement parameters
        pars.add_argument("--position_mode", type=str, default="center", help="Position mode")
        
        # Config parameters
        pars.add_argument("--mermaid_cli_path", type=str, default="mmdc", help="Mermaid CLI path")
        pars.add_argument("--use_puppeteer", type=inkex.Boolean, default=True, help="Use Puppeteer")
        pars.add_argument("--config_file", type=str, default="", help="Config file")
        pars.add_argument("--css_file", type=str, default="", help="CSS file")
        
        # Advanced parameters
        pars.add_argument("--timeout", type=int, default=30, help="Timeout")
        pars.add_argument("--viewport_width", type=int, default=1920, help="Viewport width")
        pars.add_argument("--viewport_height", type=int, default=1080, help="Viewport height")
        pars.add_argument("--keep_temp_files", type=inkex.Boolean, default=False, help="Keep temp files")
        pars.add_argument("--temp_dir", type=str, default="", help="Temp directory")
        pars.add_argument("--quiet_mode", type=inkex.Boolean, default=True, help="Quiet mode")
        
        # Inkscape options
        pars.add_argument("--inkscape_path", type=str, default="inkscape", help="Inkscape executable path")
        pars.add_argument("--pdf_poppler", type=inkex.Boolean, default=True, help="Use PDF poppler for import")
        pars.add_argument("--fit_to_content", type=inkex.Boolean, default=True, help="Fit to content (no empty space)")
    
    def effect(self):
        """Main effect function."""
        try:
            # Get Mermaid code
            if self.options.use_file and self.options.mermaid_file:
                if not os.path.exists(self.options.mermaid_file):
                    inkex.errormsg(f"File not found: {self.options.mermaid_file}")
                    return
                with open(self.options.mermaid_file, 'r', encoding='utf-8') as f:
                    mermaid_code = f.read()
            else:
                mermaid_code = self.options.mermaid_code
            
            # Clean up the code
            mermaid_code = mermaid_code.strip()
            
            if not mermaid_code:
                inkex.errormsg("No Mermaid code provided!")
                return
            
            # Check if mmdc is installed
            if not self.check_mermaid_cli():
                inkex.errormsg(f"Mermaid CLI not found at: {self.options.mermaid_cli_path}\n\n"
                             "Install with: npm install -g @mermaid-js/mermaid-cli\n\n"
                             "On Windows, you may need to use full path like:\n"
                             "C:\\Users\\YourName\\AppData\\Roaming\\npm\\mmdc.cmd")
                return
            
            # Always generate PDF first (best quality from Mermaid)
            pdf_file = self.generate_diagram_pdf(mermaid_code)
            
            if not pdf_file or not os.path.exists(pdf_file):
                inkex.errormsg("Failed to generate PDF diagram")
                return
            
            # Convert PDF using Inkscape based on output format
            if self.options.output_format == "svg":
                # Convert PDF to SVG using Inkscape and import
                self.import_pdf_as_svg(pdf_file)
            else:
                # Convert PDF to PNG using Inkscape
                png_file = self.convert_pdf_to_png(pdf_file)
                if png_file:
                    self.import_image(png_file)
            
            # Clean up temp files if needed
            if not self.options.keep_temp_files:
                try:
                    if os.path.exists(pdf_file):
                        os.remove(pdf_file)
                    input_file = pdf_file.replace('.pdf', '.mmd')
                    if os.path.exists(input_file):
                        os.remove(input_file)
                except:
                    pass
            
        except Exception as e:
            inkex.errormsg(f"Error: {str(e)}")
            import traceback
            inkex.errormsg(traceback.format_exc())
    
    def check_mermaid_cli(self):
        """Check if Mermaid CLI is installed."""
        try:
            cmd = [self.options.mermaid_cli_path, '--version']
            result = subprocess.run(cmd, 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=5,
                                  shell=True if os.name == 'nt' else False)
            return result.returncode == 0
        except:
            return False
    
    def generate_diagram_pdf(self, mermaid_code):
        """Generate diagram as PDF using Mermaid CLI."""
        # Create temp directory
        if self.options.temp_dir and os.path.exists(self.options.temp_dir):
            temp_dir = self.options.temp_dir
        else:
            temp_dir = tempfile.mkdtemp()
        
        # Create input file
        input_file = os.path.join(temp_dir, "diagram.mmd")
        with open(input_file, 'w', encoding='utf-8') as f:
            f.write(mermaid_code)
        
        # Create output PDF file path
        pdf_file = os.path.join(temp_dir, "diagram.pdf")
        
        # Build command - generate PDF
        cmd = [self.options.mermaid_cli_path, '-i', input_file, '-o', pdf_file]
        
        # Add theme
        if self.options.theme != "default":
            cmd.extend(['-t', self.options.theme])
        
        # Add background
        if self.options.background == "transparent":
            cmd.extend(['-b', 'transparent'])
        elif self.options.background != "white":
            cmd.extend(['-b', self.options.background])
        
        # Add dimensions (only if fit_to_content is false)
        if not self.options.fit_to_content:
            cmd.extend(['-w', str(self.options.width)])
            cmd.extend(['-H', str(self.options.height)])
        
        # Add config file if provided
        if self.options.config_file and os.path.exists(self.options.config_file):
            cmd.extend(['-c', self.options.config_file])
        
        # Add CSS file if provided
        if self.options.css_file and os.path.exists(self.options.css_file):
            cmd.extend(['--cssFile', self.options.css_file])
        
        # Add scale
        if self.options.scale_factor != 1.0:
            cmd.extend(['-s', str(self.options.scale_factor)])
        
        # Execute command
        try:
            if not self.options.quiet_mode:
                inkex.errormsg(f"Running: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=self.options.timeout,
                                  shell=True if os.name == 'nt' else False)
            
            if result.returncode != 0:
                inkex.errormsg(f"Mermaid CLI error:\n{result.stderr}\n{result.stdout}")
                return None
            
            if not self.options.quiet_mode and result.stdout:
                inkex.errormsg(f"Output: {result.stdout}")
            
            return pdf_file
            
        except subprocess.TimeoutExpired:
            inkex.errormsg(f"Mermaid CLI timeout ({self.options.timeout}s)")
            return None
        except Exception as e:
            inkex.errormsg(f"Error running Mermaid CLI: {str(e)}")
            return None
    
    def import_pdf_as_svg(self, pdf_file):
        """Import PDF as SVG using Inkscape CLI to convert."""
        try:
            # Create temp SVG file
            temp_dir = os.path.dirname(pdf_file)
            svg_file = os.path.join(temp_dir, "diagram_converted.svg")
            
            # Build Inkscape command to convert PDF to SVG
            cmd = [
                self.options.inkscape_path,
                pdf_file,
                '--export-type=svg',
                '--export-plain-svg',
                '--export-filename=' + svg_file
            ]
            
            # Add poppler option if enabled (better PDF import with text preservation)
            if self.options.pdf_poppler:
                cmd.insert(1, '--pdf-poppler')
            
            # Add export area option for tight cropping
            if self.options.fit_to_content:
                cmd.append('--export-area-drawing')
            
            if not self.options.quiet_mode:
                inkex.errormsg(f"Converting PDF to SVG with Inkscape: {' '.join(cmd)}")
            
            # Execute Inkscape conversion
            result = subprocess.run(cmd, 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=60,
                                  shell=False)
            
            if result.returncode != 0:
                inkex.errormsg(f"Inkscape conversion error:\n{result.stderr}")
                return
            
            if not os.path.exists(svg_file):
                inkex.errormsg("Inkscape conversion failed: SVG file not created")
                return
            
            # Read the converted SVG
            with open(svg_file, 'r', encoding='utf-8') as f:
                svg_content = f.read()
            
            # Parse SVG
            from lxml import etree
            svg_tree = etree.fromstring(svg_content.encode('utf-8'))
            
            # Get position
            x, y = self.calculate_position()
            
            # Create a group to hold the imported SVG
            group = inkex.Group()
            group.label = "Mermaid Diagram"
            group.set('transform', f'translate({x},{y})')
            
            # Add all elements from the imported SVG to the group
            for element in svg_tree:
                group.append(element)
            
            # Copy viewBox if present
            if 'viewBox' in svg_tree.attrib:
                group.set('viewBox', svg_tree.attrib['viewBox'])
            
            # Add to document
            self.svg.append(group)
            
            # Clean up temp SVG
            if not self.options.keep_temp_files:
                try:
                    os.remove(svg_file)
                except:
                    pass
            
        except Exception as e:
            inkex.errormsg(f"Error importing PDF as SVG: {str(e)}")
            import traceback
            inkex.errormsg(traceback.format_exc())
    
    def convert_pdf_to_png(self, pdf_file):
        """Convert PDF to PNG using Inkscape CLI."""
        try:
            # Create temp PNG file
            temp_dir = os.path.dirname(pdf_file)
            png_file = os.path.join(temp_dir, "diagram_converted.png")
            
            # Adjust DPI based on quality setting
            dpi = 72 * self.options.quality  # quality 1=72dpi, 2=144dpi, 3=216dpi, 4=288dpi
            
            # Build Inkscape command to convert PDF to PNG
            cmd = [
                self.options.inkscape_path, 
                pdf_file, 
                '--export-type=png',
                '--export-filename=' + png_file,
                f'--export-dpi={dpi}'
            ]
            
            # Add poppler option for better text rendering
            if self.options.pdf_poppler:
                cmd.insert(1, '--pdf-poppler')
            
            # Add export area option for tight cropping
            if self.options.fit_to_content:
                cmd.append('--export-area-drawing')
            
            if not self.options.quiet_mode:
                inkex.errormsg(f"Converting PDF to PNG: {' '.join(cmd)}")
            
            # Execute Inkscape conversion
            result = subprocess.run(cmd, 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=60,
                                  shell=False)
            
            if result.returncode != 0:
                inkex.errormsg(f"Inkscape PNG conversion error:\n{result.stderr}")
                return None
            
            if not os.path.exists(png_file):
                inkex.errormsg("PNG conversion failed: PNG file not created")
                return None
            
            return png_file
            
        except Exception as e:
            inkex.errormsg(f"Error converting PDF to PNG: {str(e)}")
            return None
    
    def import_image(self, image_file):
        """Import PNG image into document."""
        try:
            import base64
            from inkex import Image
            
            # Read image data
            with open(image_file, 'rb') as f:
                image_data = f.read()
            
            if len(image_data) == 0:
                inkex.errormsg("Generated image file is empty")
                return
            
            # Try to get image dimensions
            img_width = self.options.width
            img_height = self.options.height
            
            try:
                from PIL import Image as PILImage
                pil_image = PILImage.open(image_file)
                img_width, img_height = pil_image.size
                pil_image.close()
            except:
                # If PIL not available, use specified dimensions
                pass
            
            # Create image element
            image = Image()
            
            # Embed or link image based on option
            if self.options.embed_image:
                # Embed image
                encoded = base64.b64encode(image_data).decode('ascii')
                image.set('{http://www.w3.org/1999/xlink}href', f'data:image/png;base64,{encoded}')
            else:
                # Link to external file
                abs_path = os.path.abspath(image_file)
                if os.name == 'nt':
                    abs_path = 'file:///' + abs_path.replace('\\', '/')
                else:
                    abs_path = 'file://' + abs_path
                image.set('{http://www.w3.org/1999/xlink}href', abs_path)
            
            # Set position
            x, y = self.calculate_position()
            image.set('x', str(x))
            image.set('y', str(y))
            
            # Use actual image dimensions
            image.set('width', str(img_width))
            image.set('height', str(img_height))
            image.set('preserveAspectRatio', 'xMidYMid meet')
            
            # Add to document
            self.svg.append(image)
            
            # Clean up temp PNG only if embedded
            if self.options.embed_image and not self.options.keep_temp_files:
                try:
                    os.remove(image_file)
                except:
                    pass
            
        except Exception as e:
            inkex.errormsg(f"Error importing image: {str(e)}")
            import traceback
            inkex.errormsg(traceback.format_exc())
    
    def calculate_position(self):
        """Calculate insertion position."""
        # Get canvas dimensions
        width = self.svg.viewport_width - 1000
        height = self.svg.viewport_height - 1000
        
        # For fit_to_content, we don't know exact dimensions yet
        # Use canvas center as default
        diagram_width = 0
        diagram_height = 0
        
        if self.options.position_mode == "center":
            x = (width - diagram_width) / 2
            y = (height - diagram_height) / 2
        elif self.options.position_mode == "top_left":
            x = 0
            y = 0
        elif self.options.position_mode == "top_center":
            x = width / 2
            y = 0
        elif self.options.position_mode == "top_right":
            x = width - diagram_width
            y = 0
        elif self.options.position_mode == "bottom_left":
            x = 0
            y = height - diagram_height
        elif self.options.position_mode == "bottom_center":
            x = width / 2
            y = height - diagram_height
        elif self.options.position_mode == "bottom_right":
            x = width - diagram_width
            y = height - diagram_height
        else:  # cursor or default
            x = width / 2
            y = height / 2
        
        return x, y


if __name__ == '__main__':
    MermaidGenerator().run()