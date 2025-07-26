import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="Programación Agrícola", layout="wide")
st.title("📆 Programación de Aplicaciones - La Judea")

# Inputs del usuario
archivo_estado = st.file_uploader("📋 Archivo Estado de Cultivo", type="xlsx")
archivo_aplicaciones = st.file_uploader("🌱 Archivo Programa de Aplicaciones", type="xlsx")
archivo_insumos = st.file_uploader("🧪 Archivo Base de Insumos", type="xlsx")
col1, col2 = st.columns(2)
with col1:
    fecha_inicio = st.date_input("Fecha de inicio", value=datetime.today())
with col2:
    num_semanas = st.number_input("Número de semanas", min_value=1, max_value=12, value=4)

@st.cache_data
def generar_calendario(fecha, semanas):
    return [(i + 1, fecha + timedelta(weeks=i), fecha + timedelta(weeks=i, days=6)) for i in range(semanas)]

if st.button("🚀 Generar Programación"):
    try:
        if not (archivo_estado and archivo_aplicaciones and archivo_insumos):
            st.warning("Debes subir los tres archivos para continuar.")
            st.stop()

        df_estado = pd.read_excel(archivo_estado)
        df_aplicaciones = pd.read_excel(archivo_aplicaciones)
        df_insumos_base = pd.read_excel(archivo_insumos, sheet_name="Base")

        columnas_estado = ['Lote', 'Bloque', 'Area_ha', 'Estado', 'Fecha_Estado', 'G_Forza']
        columnas_aplic = ['Aplicacion', 'Edad_calendario', 'Estado_valido']
        for col in columnas_estado:
            assert col in df_estado.columns, f"Falta columna en Estado: {col}"
        for col in columnas_aplic:
            assert col in df_aplicaciones.columns, f"Falta columna en Aplicaciones: {col}"

        df_estado['Fecha_Estado'] = pd.to_datetime(df_estado['Fecha_Estado'], dayfirst=True)
        semanas = generar_calendario(fecha_inicio, num_semanas)
        resultados = []

        for semana, inicio, fin in semanas:
            for (lote, bloque), grupo in df_estado.groupby(['Lote', 'Bloque']):
                estado_actual = grupo.sort_values('Fecha_Estado').iloc[-1]
                fecha_estado = estado_actual['Fecha_Estado']
                estado = estado_actual['Estado']
                g_forza = estado_actual['G_Forza']
                area = round(estado_actual['Area_ha'], 2)

                for dia in range(7):
                    fecha_aplic = inicio + timedelta(days=dia)
                    edad = (pd.Timestamp(fecha_aplic) - fecha_estado).days  # ✅ Corrección aplicada

                    for _, aplic in df_aplicaciones.iterrows():
                        if estado == aplic['Estado_valido'] and edad == aplic['Edad_calendario']:
                            resultados.append({
                                'Semana': semana,
                                'Aplicacion': aplic['Aplicacion'],
                                'Finca': 'La Judea',
                                'Lote': lote,
                                'Bloque': bloque,
                                'Area': area,
                                'G_Forza': g_forza,
                                'Fecha Aplicacion': fecha_aplic
                            })

        df_programacion = pd.DataFrame(resultados)
        if df_programacion.empty:
            st.warning("No se encontraron aplicaciones programadas.")
            st.stop()

        df_programacion = df_programacion.sort_values(['Semana', 'Aplicacion', 'Lote'])
        st.subheader("📄 Programación Generada")
        st.dataframe(df_programacion)

        df_insumos = pd.merge(df_programacion, df_insumos_base, on="Aplicacion", how="left")
        df_insumos["Cantidad"] = df_insumos["Area"] * df_insumos["Dosis"]

        semanas_dict = {sem: f"Sem {sem} {ini.strftime('%d/%m')} - {fin.strftime('%d/%m')}"
                        for sem, ini, fin in semanas}
        df_insumos['Rango Semana'] = df_insumos['Semana'].map(semanas_dict)

        df_pivot = df_insumos.groupby(
            ['Tipo_Insumo', 'Cod_Insumo', 'Insumo', 'UM', 'Rango Semana']
        )['Cantidad'].sum().unstack(fill_value=0).reset_index()

        df_pivot['Total'] = df_pivot.iloc[:, 5:].sum(axis=1)
        df_pivot = df_pivot.sort_values(by=['Tipo_Insumo', 'Cod_Insumo'])

        st.subheader("📊 Resumen de Insumos por Semana")
        st.dataframe(df_pivot)

        from io import BytesIO
        from openpyxl import Workbook

        output = BytesIO()
        wb = Workbook()
        ws_prog = wb.active
        ws_prog.title = "Programacion"
        ws_prog.append(df_programacion.columns.tolist())
        for _, row in df_programacion.iterrows():
            ws_prog.append(list(row))

        ws_insumos = wb.create_sheet("Resumen_Insumos")
        ws_insumos.append(df_pivot.columns.tolist())
        for _, row in df_pivot.iterrows():
            ws_insumos.append(list(row))

        wb.save(output)
        output.seek(0)

        st.download_button(
            label="⬇️ Descargar archivo Excel",
            data=output,
            file_name=f"Programacion_LaJudea_{fecha_inicio.strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        st.success("✅ Programación creada con éxito")

    except Exception as e:
        st.error(f"❌ Error: {str(e)}")