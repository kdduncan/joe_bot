"""Visualization Agent - Creates temporary charts for the Summary Agent.

This tool generates temporary PNG visualizations that are deleted after use.
"""
import logging
import tempfile
import os
from typing import Dict, Any, List, Optional
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for server use

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VisualizationAgent:
    """Generate temporary charts and graphs for job market data."""
    
    def __init__(self):
        """Initialize the Visualization Agent with temp directory."""
        # Use system temp directory
        self.temp_dir = Path(tempfile.gettempdir()) / 'joe_bot_charts'
        self.temp_dir.mkdir(exist_ok=True)
        logger.info(f"VisualizationAgent initialized (temp dir: {self.temp_dir})")
    
    
    def create_chart(self, chart_type: str, data: Dict[str, Any], 
                     title: str, filename: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a temporary chart that will be deleted after use.
        
        Args:
            chart_type: Type of chart - "bar", "line", "pie", "comparison"
            data: Data to visualize (format depends on chart type)
            title: Chart title
            filename: Optional custom filename (without extension)
        
        Returns:
            Dictionary with temporary chart path and metadata
        """
        try:
            if not filename:
                # Generate filename from title
                filename = title.lower().replace(' ', '_').replace('/', '_')[:50]
            
            # Create in temp directory
            filepath = self.temp_dir / f"{filename}.png"
            
            logger.info(f"Creating temporary {chart_type} chart: {title}")
            
            if chart_type == "bar":
                result = self._create_bar_chart(data, title, filepath)
            elif chart_type == "line":
                result = self._create_line_chart(data, title, filepath)
            elif chart_type == "pie":
                result = self._create_pie_chart(data, title, filepath)
            elif chart_type == "comparison":
                result = self._create_comparison_chart(data, title, filepath)
            else:
                return {"error": f"Unknown chart type: {chart_type}"}
            
            # Mark result as temporary
            if result.get('success'):
                result['temporary'] = True
                result['note'] = 'Chart will be auto-deleted after use'
            
            return result
        
        except Exception as e:
            logger.error(f"Error creating chart: {e}")
            return {"error": str(e)}
    
    def cleanup_chart(self, chart_path: str) -> bool:
        """
        Delete a temporary chart file.
        
        Args:
            chart_path: Path to the chart to delete
        
        Returns:
            True if deleted successfully
        """
        try:
            path = Path(chart_path)
            if path.exists():
                path.unlink()
                logger.info(f"Deleted temporary chart: {chart_path}")
                return True
            return False
        except Exception as e:
            logger.warning(f"Failed to delete chart {chart_path}: {e}")
            return False
    
    def _create_bar_chart(self, data: Dict[str, Any], title: str, 
                         filepath: Path) -> Dict[str, Any]:
        """Create a bar chart."""
        labels = data.get('labels', [])
        values = data.get('values', [])
        
        if not labels or not values:
            return {"error": "Missing labels or values for bar chart"}
        
        # Limit to top 15 for readability
        if len(labels) > 15:
            labels = labels[:15]
            values = values[:15]
        
        fig, ax = plt.subplots(figsize=(12, 6))
        bars = ax.bar(range(len(labels)), values, color='#5865F2', alpha=0.8)
        
        ax.set_xlabel(data.get('x_label', 'Category'), fontsize=12)
        ax.set_ylabel(data.get('y_label', 'Count'), fontsize=12)
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=45, ha='right')
        ax.grid(axis='y', alpha=0.3)
        
        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{int(height)}', ha='center', va='bottom', fontsize=9)
        
        plt.tight_layout()
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        
        return {
            "success": True,
            "chart_path": str(filepath),
            "chart_type": "bar",
            "data_points": len(labels)
        }
    
    def _create_line_chart(self, data: Dict[str, Any], title: str, 
                          filepath: Path) -> Dict[str, Any]:
        """Create a line chart for trends over time."""
        labels = data.get('labels', [])
        values = data.get('values', [])
        
        if not labels or not values:
            return {"error": "Missing labels or values for line chart"}
        
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.plot(labels, values, marker='o', linewidth=2, 
               markersize=8, color='#5865F2')
        
        ax.set_xlabel(data.get('x_label', 'Time Period'), fontsize=12)
        ax.set_ylabel(data.get('y_label', 'Count'), fontsize=12)
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        
        # Add value labels
        for x, y in zip(labels, values):
            ax.text(x, y, f'{int(y)}', ha='center', va='bottom', fontsize=9)
        
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        
        return {
            "success": True,
            "chart_path": str(filepath),
            "chart_type": "line",
            "data_points": len(labels)
        }
    
    def _create_pie_chart(self, data: Dict[str, Any], title: str, 
                         filepath: Path) -> Dict[str, Any]:
        """Create a pie chart for distribution."""
        labels = data.get('labels', [])
        values = data.get('values', [])
        
        if not labels or not values:
            return {"error": "Missing labels or values for pie chart"}
        
        # Limit to top 10 for readability
        if len(labels) > 10:
            other_sum = sum(values[10:])
            labels = labels[:10] + ['Others']
            values = values[:10] + [other_sum]
        
        fig, ax = plt.subplots(figsize=(10, 8))
        wedges, texts, autotexts = ax.pie(
            values, 
            labels=labels, 
            autopct='%1.1f%%',
            startangle=90,
            colors=plt.cm.Set3.colors
        )
        
        ax.set_title(title, fontsize=14, fontweight='bold')
        
        # Improve text readability
        for text in texts:
            text.set_fontsize(10)
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontweight('bold')
            autotext.set_fontsize(9)
        
        plt.tight_layout()
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        
        return {
            "success": True,
            "chart_path": str(filepath),
            "chart_type": "pie",
            "data_points": len(labels)
        }
    
    def _create_comparison_chart(self, data: Dict[str, Any], title: str,
                                filepath: Path) -> Dict[str, Any]:
        """Create a grouped bar chart for comparisons."""
        categories = data.get('categories', [])
        series_data = data.get('series', {})  # {series_name: [values]}
        
        if not categories or not series_data:
            return {"error": "Missing categories or series data"}
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        x = range(len(categories))
        width = 0.8 / len(series_data)
        colors = ['#5865F2', '#ED4245', '#57F287', '#FEE75C']
        
        for i, (series_name, values) in enumerate(series_data.items()):
            offset = width * i - (width * len(series_data) / 2) + width/2
            bars = ax.bar([xi + offset for xi in x], values, width, 
                         label=series_name, color=colors[i % len(colors)], alpha=0.8)
            
            # Add value labels
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{int(height)}', ha='center', va='bottom', fontsize=8)
        
        ax.set_xlabel('Category', fontsize=12)
        ax.set_ylabel(data.get('y_label', 'Count'), fontsize=12)
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(categories, rotation=45, ha='right')
        ax.legend()
        ax.grid(axis='y', alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        
        return {
            "success": True,
            "chart_path": str(filepath),
            "chart_type": "comparison",
            "series_count": len(series_data),
            "data_points": len(categories)
        }
    
    def get_tool_definition(self) -> Dict[str, Any]:
        """
        Return OpenAI tool definition for chart creation.
        Used by Summary Agent to call this as a tool.
        """
        return {
            "type": "function",
            "function": {
                "name": "create_chart",
                "description": "Create a PNG chart/graph to visualize job market data. Use this when users ask for graphs, charts, trends, or visual representations.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "chart_type": {
                            "type": "string",
                            "enum": ["bar", "line", "pie", "comparison"],
                            "description": "Type of chart: 'bar' for comparisons, 'line' for trends over time, 'pie' for distributions, 'comparison' for multi-series comparison"
                        },
                        "data": {
                            "type": "object",
                            "description": "Data to visualize",
                            "properties": {
                                "labels": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "X-axis labels or categories"
                                },
                                "values": {
                                    "type": "array",
                                    "items": {"type": "number"},
                                    "description": "Y-axis values (for bar, line, pie)"
                                },
                                "categories": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Categories for comparison charts"
                                },
                                "series": {
                                    "type": "object",
                                    "description": "Multiple data series for comparison (e.g., {2023: [val1, val2], 2024: [val1, val2]})"
                                },
                                "x_label": {"type": "string"},
                                "y_label": {"type": "string"}
                            },
                            "required": ["labels", "values"]
                        },
                        "title": {
                            "type": "string",
                            "description": "Chart title"
                        },
                        "filename": {
                            "type": "string",
                            "description": "Optional custom filename (without extension)"
                        }
                    },
                    "required": ["chart_type", "data", "title"]
                }
            }
        }
