import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = PROJECT_ROOT / "data" / "02_realisasi_anggaran_klasifikasi.csv"
GEOJSON_PATH = PROJECT_ROOT / "data" / "indonesia_provinces.geojson"

BOUNDARY_VERSION = "v2026.06"
BOUNDARY_SOURCE_URL = (
    "https://github.com/dmxsan/indonesia-admin-boundaries/tree/"
    "v2026.06/processed-data/simplified/02-provinces"
)
BOUNDARY_LICENSE_URL = (
    "https://github.com/dmxsan/indonesia-admin-boundaries/blob/"
    "v2026.06/LICENSE"
)
BIG_SOURCE_URL = "https://tanahair.indonesia.go.id/"

PROVINCE_NAME_MAP = {
    "Aceh": "Aceh",
    "Bali": "Bali",
    "DKI Jakarta": "Daerah Khusus Ibukota Jakarta",
    "Jawa Barat": "Jawa Barat",
    "Jawa Tengah": "Jawa Tengah",
    "Jawa Timur": "Jawa Timur",
    "Kalimantan Timur": "Kalimantan Timur",
    "Lampung": "Lampung",
    "NTB": "Nusa Tenggara Barat",
    "NTT": "Nusa Tenggara Timur",
    "Papua": "Papua",
    "Riau": "Riau",
    "Sulawesi Selatan": "Sulawesi Selatan",
    "Sumatera Barat": "Sumatera Barat",
    "Sumatera Utara": "Sumatera Utara",
}


@st.cache_data
def load_data():
    return pd.read_csv(CSV_PATH)


@st.cache_data
def load_geojson():
    with GEOJSON_PATH.open(encoding="utf-8") as geojson_file:
        return json.load(geojson_file)


st.title("Peta IKPA Indonesia")
st.markdown("## Rata-rata IKPA Satker per Provinsi")
st.caption(
    "Nilai merupakan agregasi dataset satker, bukan nilai resmi pemerintah provinsi."
)
st.caption(
    f"Sumber batas: [Badan Informasi Geospasial (BIG)]({BIG_SOURCE_URL}), "
    f"edisi 2026 Semester 1, disederhanakan pada rilis "
    f"[{BOUNDARY_VERSION}]({BOUNDARY_SOURCE_URL})."
)
st.caption(
    "GeoJSON merupakan olahan data BIG; periksa "
    f"[ketentuan penggunaan]({BOUNDARY_LICENSE_URL}), terutama untuk "
    "penggunaan komersial."
)

data = load_data()
geojson = load_geojson()
geojson_features = geojson.get("features", [])
geojson_name_list = [
    feature.get("properties", {}).get("WADMPR") for feature in geojson_features
]
geojson_names = {
    name for name in geojson_name_list if name
}
csv_province_names = set(data["provinsi"].dropna().unique())
duplicate_boundary_names = sorted(
    name for name in geojson_names if geojson_name_list.count(name) > 1
)
unnamed_boundary_count = sum(name is None for name in geojson_name_list)

if len(geojson_names) != 38:
    st.warning(
        f"GeoJSON {BOUNDARY_VERSION} memuat {len(geojson_names)} nama provinsi; "
        "versi yang diharapkan memuat 38 provinsi."
    )
if unnamed_boundary_count:
    st.warning(
        f"{unnamed_boundary_count} fitur GeoJSON tidak memiliki nama WADMPR "
        "dan tidak dapat dipadankan."
    )
if duplicate_boundary_names:
    st.error(
        "Nama provinsi GeoJSON tidak unik: " + ", ".join(duplicate_boundary_names)
    )
    st.stop()

unmapped_csv_names = sorted(csv_province_names - set(PROVINCE_NAME_MAP))
missing_boundary_names = sorted(
    {
        PROVINCE_NAME_MAP[name]
        for name in csv_province_names & set(PROVINCE_NAME_MAP)
        if PROVINCE_NAME_MAP[name] not in geojson_names
    }
)
papua_features = {
    name for name in geojson_names if name == "Papua" or name.startswith("Papua ")
}
papua_match_valid = (
    "Papua" not in csv_province_names
    or (
        PROVINCE_NAME_MAP.get("Papua") == "Papua"
        and "Papua" in geojson_names
    )
)

if unmapped_csv_names:
    st.warning(
        "Nama provinsi CSV belum memiliki pemetaan: "
        + ", ".join(unmapped_csv_names)
        + ". Baris tersebut tidak dipetakan ke poligon."
    )
if missing_boundary_names:
    st.warning(
        "Nama tujuan pemetaan tidak ditemukan pada batas "
        f"{BOUNDARY_VERSION}: "
        + ", ".join(missing_boundary_names)
        + ". Periksa kesesuaian versi batas."
    )
if not papua_match_valid:
    st.warning(
        "Nama Papua pada CSV tidak dapat dipadankan secara aman dengan "
        "batas Papua pada GeoJSON. Nilainya tidak dipindahkan ke provinsi "
        "hasil pemekaran."
    )
elif "Papua" in csv_province_names:
    if "Papua" not in papua_features:
        st.warning(
            "Fitur Papua tidak ditemukan pada GeoJSON; data Papua tidak "
            "dipindahkan ke provinsi hasil pemekaran."
        )
    else:
        st.warning(
            "Label CSV Papua hanya dipadankan ke poligon Papua pada batas "
            "2026; nilainya tidak disalin ke provinsi hasil pemekaran. CSV "
            "tidak mencantumkan tahun/cakupan batas, jadi kesesuaian geografis "
            "Papua perlu dikonfirmasi terhadap sumber dataset."
        )

with st.sidebar:
    st.header("Filter Peta IKPA")
    kementerian_pilihan = st.multiselect(
        "Nama kementerian",
        options=sorted(data["nama_kementerian"].dropna().unique()),
        default=sorted(data["nama_kementerian"].dropna().unique()),
    )
    tipe_pilihan = st.multiselect(
        "Tipe satker",
        options=sorted(data["tipe_satker"].dropna().unique()),
        default=sorted(data["tipe_satker"].dropna().unique()),
    )
    jenis_belanja_pilihan = st.multiselect(
        "Jenis belanja utama",
        options=sorted(data["jenis_belanja_utama"].dropna().unique()),
        default=sorted(data["jenis_belanja_utama"].dropna().unique()),
    )

filtered_data = data[
    data["nama_kementerian"].isin(kementerian_pilihan)
    & data["tipe_satker"].isin(tipe_pilihan)
    & data["jenis_belanja_utama"].isin(jenis_belanja_pilihan)
].copy()
filtered_data["provinsi_peta"] = filtered_data["provinsi"].map(PROVINCE_NAME_MAP)

satker_count = filtered_data["kode_satker"].nunique()
overall_mean = filtered_data["skor_ikpa"].mean()
metric_columns = st.columns(3)
metric_columns[0].metric(
    "Provinsi dengan data",
    int(
        filtered_data.loc[
            filtered_data["provinsi_peta"].isin(geojson_names)
            & filtered_data["skor_ikpa"].notna(),
            "provinsi_peta",
        ].nunique()
    ),
)
metric_columns[1].metric("Jumlah satker", f"{satker_count:,}")
metric_columns[2].metric(
    "Rata-rata IKPA seluruh satker",
    f"{overall_mean:.2f}" if pd.notna(overall_mean) else "—",
)

province_data = filtered_data[
    filtered_data["provinsi_peta"].isin(geojson_names)
].copy()
province_summary = (
    province_data.groupby("provinsi_peta", as_index=False)
    .agg(
        jumlah_satker=("kode_satker", "nunique"),
        rata_ikpa=("skor_ikpa", "mean"),
        median_ikpa=("skor_ikpa", "median"),
        minimum_ikpa=("skor_ikpa", "min"),
        maksimum_ikpa=("skor_ikpa", "max"),
        total_pagu=("pagu_miliar", "sum"),
    )
    .rename(columns={"provinsi_peta": "provinsi"})
)

map_data = province_summary[province_summary["rata_ikpa"].notna()].copy()
map_data = map_data.sort_values("provinsi")
map_names = set(map_data["provinsi"])
no_data_names = sorted(geojson_names - map_names)
features_by_name = {
    feature["properties"]["WADMPR"]: feature for feature in geojson_features
}

figure = go.Figure()
if no_data_names:
    no_data_geojson = {
        "type": "FeatureCollection",
        "features": [features_by_name[name] for name in no_data_names],
    }
    # This constant styles the no-data layer only; it is not an IKPA value.
    figure.add_trace(
        go.Choroplethmap(
            geojson=no_data_geojson,
            featureidkey="properties.WADMPR",
            locations=no_data_names,
            z=[0.5] * len(no_data_names),
            zmin=0,
            zmax=1,
            colorscale=[[0, "#d3d3d3"], [1, "#d3d3d3"]],
            showscale=False,
            marker_opacity=0.8,
            marker_line_color="#ffffff",
            marker_line_width=0.5,
            hovertemplate="%{location}<br>Tidak ada data<extra></extra>",
            name="Tidak ada data",
        )
    )

if not map_data.empty:
    data_geojson = {
        "type": "FeatureCollection",
        "features": [features_by_name[name] for name in map_data["provinsi"]],
    }
    map_tooltip_fields = [
        "jumlah_satker",
        "rata_ikpa",
        "median_ikpa",
        "minimum_ikpa",
        "maksimum_ikpa",
        "total_pagu",
    ]
    customdata = map_data[map_tooltip_fields].to_numpy().tolist()
    figure.add_trace(
        go.Choroplethmap(
            geojson=data_geojson,
            featureidkey="properties.WADMPR",
            locations=map_data["provinsi"],
            z=map_data["rata_ikpa"],
            zmin=0,
            zmax=100,
            colorscale=[
                [0, "#d73027"],
                [0.5, "#fee08b"],
                [1, "#1a9850"],
            ],
            colorbar={"title": "Rata-rata IKPA", "tick0": 0, "dtick": 20},
            marker_opacity=0.9,
            marker_line_color="#ffffff",
            marker_line_width=0.5,
            customdata=customdata,
            hovertemplate=(
                "<b>%{location}</b>"
                "<br>Jumlah satker unik: %{customdata[0]:.0f}"
                "<br>Rata-rata IKPA: %{customdata[1]:.2f}"
                "<br>Median IKPA: %{customdata[2]:.2f}"
                "<br>IKPA minimum: %{customdata[3]:.2f}"
                "<br>IKPA maksimum: %{customdata[4]:.2f}"
                "<br>Total pagu: Rp %{customdata[5]:,.2f} miliar"
                "<extra></extra>"
            ),
            name="Rata-rata IKPA",
        )
    )

figure.update_layout(
    map={
        "style": "carto-positron",
        "center": {"lat": -2, "lon": 118},
        "zoom": 3.3,
    },
    height=700,
    margin={"r": 0, "t": 0, "l": 0, "b": 0},
    legend={"title": "Keterangan"},
)

st.caption("Warna abu-abu pada peta menunjukkan: Tidak ada data.")
st.plotly_chart(figure, width="stretch")
st.caption(
    "Batas wilayah disederhanakan untuk visualisasi dan tidak dapat dijadikan "
    "referensi hukum. Sumber data batas: BIG; ketentuan penggunaan BIG tetap berlaku."
)

st.subheader("Rata-rata IKPA per Provinsi")
if not province_summary.empty:
    bar_data = province_summary[province_summary["rata_ikpa"].notna()].sort_values(
        "rata_ikpa",
        ascending=False,
    )
    bar_figure = go.Figure(
        go.Bar(
            x=bar_data["rata_ikpa"],
            y=bar_data["provinsi"],
            orientation="h",
            customdata=bar_data[["jumlah_satker"]].to_numpy(),
            hovertemplate=(
                "<b>%{y}</b><br>Rata-rata IKPA: %{x:.2f}"
                "<br>Jumlah satker unik: %{customdata[0]:.0f}<extra></extra>"
            ),
        )
    )
    bar_figure.update_layout(
        xaxis_title="Rata-rata IKPA",
        yaxis_title=None,
        yaxis={"categoryorder": "total ascending"},
        height=max(350, 28 * len(bar_data)),
        margin={"r": 20, "t": 10, "l": 10, "b": 40},
    )
    st.plotly_chart(bar_figure, width="stretch")
else:
    st.info("Tidak ada skor IKPA yang dapat ditampilkan untuk filter ini.")

st.subheader("Detail Satker per Provinsi")
available_provinces = sorted(
    province_summary.loc[
        province_summary["rata_ikpa"].notna(),
        "provinsi",
    ].unique()
)
if available_provinces:
    selected_province = st.selectbox("Pilih provinsi", available_provinces)
    detail_columns = [
        "kode_satker",
        "nama_kementerian",
        "skor_ikpa",
        "pagu_miliar",
        "realisasi_tw3_persen",
    ]
    detail_data = (
        province_data.loc[
            province_data["provinsi_peta"] == selected_province,
            detail_columns,
        ]
        .sort_values("skor_ikpa", ascending=False)
        .reset_index(drop=True)
    )
    st.dataframe(detail_data, width="stretch", hide_index=True)
    st.download_button(
        "Unduh tabel detail sebagai CSV",
        data=detail_data.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"detail_satker_{selected_province.replace(' ', '_').lower()}.csv",
        mime="text/csv",
    )
else:
    st.info("Tidak ada provinsi dengan skor IKPA untuk filter ini.")
