#!/usr/bin/env python3
"""Script para verificar estructura de tablas de fórmulas"""

import os
import psycopg2
from database import DatabasePool

def check_formula_tables():
    try:
        # Inicializar pool de base de datos
        DatabasePool.init_pool()
        db = DatabasePool.get_connection()
        cur = db.cursor()
        
        tables = [
            'presentacion',
            'formulas_cce_g',
            'formulas_cce_c',
            'formulas_cce_qt',
            'formulas_bacc_g',
            'formulas_bacc_c',
            'formulas_bacc_qt',
            'formulas_backup',
            'colorante',
        ]
        
        for table in tables:
            print(f"\n📋 TABLA: {table}")
            print("="*50)
            
            try:
                # Obtener estructura de la tabla
                cur.execute(f"""
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns 
                    WHERE table_name = '{table}'
                    ORDER BY ordinal_position
                """)
                columns = cur.fetchall()
                
                if columns:
                    print("Columnas:")
                    for col in columns:
                        print(f"  - {col[0]} ({col[1]}) - Nullable: {col[2]} - Default: {col[3]}")
                    
                    # Obtener algunos datos de muestra
                    cur.execute(f"SELECT * FROM {table} LIMIT 3")
                    sample_data = cur.fetchall()
                    
                    if sample_data:
                        print(f"\n📝 Datos de muestra ({len(sample_data)} filas):")
                        for i, row in enumerate(sample_data, 1):
                            print(f"  Fila {i}: {row}")
                    else:
                        print("⚠️ No hay datos en la tabla")
                else:
                    print("❌ Tabla no encontrada")
                    
            except Exception as e:
                print(f"❌ Error consultando {table}: {e}")
        
        cur.close()
        db.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        DatabasePool.close_pool()

if __name__ == "__main__":
    check_formula_tables()