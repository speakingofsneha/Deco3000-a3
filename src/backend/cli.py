import typer
import os
import json
from pathlib import Path
from typing import Optional
import logging
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.panel import Panel

from .processing_service import PDFProcessingService
from .models import PDFProcessingRequest
from .slide_generator import SlideGenerator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Typer app
app = typer.Typer(
    name="pdf-to-slides",
    help="Convert PDF documents to structured slide decks using AI",
    add_completion=False
)

# Initialize console for rich output
console = Console()

@app.command()
def process(
    pdf_path: str = typer.Argument(..., help="Path to the PDF file to process"),
    output_dir: Optional[str] = typer.Option(None, "--output", "-o", help="Output directory for generated files"),
    max_chunks: int = typer.Option(1000, "--max-chunks", help="Maximum number of chunks to process"),
    chunk_size: int = typer.Option(500, "--chunk-size", help="Size of each text chunk"),
    overlap: int = typer.Option(50, "--overlap", help="Overlap between chunks"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging")
):
    """Process a PDF file and generate a slide deck"""
    
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Validate inputs
    if not os.path.exists(pdf_path):
        console.print(f"[red]Error: PDF file not found: {pdf_path}[/red]")
        raise typer.Exit(1)
    
    if not pdf_path.lower().endswith('.pdf'):
        console.print("[red]Error: File must be a PDF[/red]")
        raise typer.Exit(1)
    
    # Set up output directory
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        os.chdir(output_dir)
    
    # Initialize services
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Initializing services...", total=None)
            
            processing_service = PDFProcessingService()
            
            progress.update(task, description="Processing PDF...")
            
            # Create processing request
            request = PDFProcessingRequest(
                pdf_path=pdf_path,
                max_chunks=max_chunks,
                chunk_size=chunk_size,
                overlap=overlap
            )
            
            # Process PDF
            response = processing_service.process_pdf(request)
    
    except Exception as e:
        console.print(f"[red]Error initializing services: {str(e)}[/red]")
        raise typer.Exit(1)
    
    if response.success:
        console.print(f"[green]✓ PDF processed successfully in {response.processing_time:.2f} seconds[/green]")
        
        # Display slide deck summary
        slide_deck = response.slide_deck
        if slide_deck:
            display_slide_summary(slide_deck)
            
            # Inform where the processing service saved the file
            pdf_name = Path(pdf_path).stem
            output_file = Path("outputs") / f"{pdf_name}.json"
            console.print(f"[green]✓ Slide deck saved to: {output_file}[/green]")
            
            # Display statistics
            slide_generator = SlideGenerator()
            stats = slide_generator.get_slide_statistics(slide_deck)
            display_statistics(stats)
    else:
        console.print(f"[red]Error processing PDF: {response.message}[/red]")
        raise typer.Exit(1)

@app.command()
def list_slides(
    json_file: str = typer.Argument(..., help="Path to the slide deck JSON file")
):
    """List slides from a generated slide deck"""
    
    if not os.path.exists(json_file):
        console.print(f"[red]Error: File not found: {json_file}[/red]")
        raise typer.Exit(1)
    
    try:
        slide_generator = SlideGenerator()
        slide_deck = slide_generator.load_from_json(json_file)
        
        display_slide_list(slide_deck)
        
    except Exception as e:
        console.print(f"[red]Error loading slide deck: {str(e)}[/red]")
        raise typer.Exit(1)

@app.command()
def stats(
    json_file: str = typer.Argument(..., help="Path to the slide deck JSON file")
):
    """Show statistics for a slide deck"""
    
    if not os.path.exists(json_file):
        console.print(f"[red]Error: File not found: {json_file}[/red]")
        raise typer.Exit(1)
    
    try:
        slide_generator = SlideGenerator()
        slide_deck = slide_generator.load_from_json(json_file)
        stats = slide_generator.get_slide_statistics(slide_deck)
        
        display_statistics(stats)
        
    except Exception as e:
        console.print(f"[red]Error loading slide deck: {str(e)}[/red]")
        raise typer.Exit(1)

def display_slide_summary(slide_deck):
    """Display a summary of the slide deck"""
    console.print(f"\n[bold blue]Slide Deck: {slide_deck.title}[/bold blue]")
    console.print(f"[dim]Source: {slide_deck.source_pdf}[/dim]")
    console.print(f"[dim]Created: {slide_deck.created_at}[/dim]")
    console.print(f"[dim]Total slides: {len(slide_deck.slides)}[/dim]\n")

def display_slide_list(slide_deck):
    """Display a list of all slides"""
    console.print(f"\n[bold blue]Slide Deck: {slide_deck.title}[/bold blue]\n")
    
    for i, slide in enumerate(slide_deck.slides, 1):
        console.print(f"[bold]{i}. {slide.title}[/bold]")
        console.print(f"   Type: {slide.type}")
        console.print(f"   Bullets: {len(slide.content)}")
        
        if slide.content:
            console.print("   Content preview:")
            for bullet in slide.content[:3]:  # Show first 3 bullets
                console.print(f"   • {bullet.text[:100]}{'...' if len(bullet.text) > 100 else ''}")
            if len(slide.content) > 3:
                console.print(f"   ... and {len(slide.content) - 3} more")
        
        console.print()

def display_statistics(stats):
    """Display slide deck statistics"""
    table = Table(title="Slide Deck Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="magenta")
    
    table.add_row("Total Slides", str(stats["total_slides"]))
    table.add_row("Content Slides", str(stats["content_slides"]))
    table.add_row("Title Slides", str(stats["title_slides"]))
    table.add_row("Total Bullets", str(stats["total_bullets"]))
    table.add_row("Slides with Provenance", str(stats["slides_with_provenance"]))
    table.add_row("Avg Bullets per Slide", f"{stats['average_bullets_per_slide']:.1f}")
    
    console.print(table)

@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", "--host", help="Host to bind the server to"),
    port: int = typer.Option(8000, "--port", help="Port to bind the server to")
):
    """Start the FastAPI server"""
    
    console.print(f"[green]Starting server on {host}:{port}[/green]")
    
    import uvicorn
    uvicorn.run("src.backend.api:app", host=host, port=port, reload=True)

if __name__ == "__main__":
    app()