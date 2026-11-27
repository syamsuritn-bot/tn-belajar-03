import streamlit as st
import pandas as pd
import pickle
import altair as alt
from pathlib import Path

MODEL_PATH = Path(__file__).resolve().parents[1] / "models" / "Best_model.pkcls"


@st.cache_resource
def load_model():
    with MODEL_PATH.open("rb") as model_file:
        return pickle.load(model_file)

st.title("Dashboard Analitik DJPb")

# Sidebar Filter
st.sidebar.header("Menu Filter")
opsi = st.sidebar.selectbox("Pilih Model:", ["Klasifikasi", "Regresi"])

data = pd.read_csv("data/02_realisasi_anggaran_klasifikasi.csv")

tab_prediksi, tab_visualisasi = st.tabs(["Menu Prediksi", "Visualisasi"])

with tab_prediksi:
    st.header("Prediksi Realisasi 95%")
    st.markdown("Masukkan data input berikut dan klik tombol untuk melihat hasil prediksi.")

    col1, col2 = st.columns(2)
    with col1:
        jumlah_spm = st.number_input(
            "Jumlah SPM",
            min_value=1,
            max_value=200,
            value=10,
            step=1,
            format="%d",
        )
        revisi_dipa = st.number_input(
            "Revisi DIPA",
            min_value=0,
            max_value=5,
            value=1,
            step=1,
            format="%d",
        )
        deviasi_rpd_persen = st.number_input(
            "Deviasi RPD (%)",
            min_value=0.00,
            max_value=30.00,
            value=5.50,
            format="%.2f",
        )
    with col2:
        skor_ikpa = st.number_input(
            "Skor IKPA",
            min_value=70.00,
            max_value=100.00,
            value=85.00,
            format="%.2f",
        )
        tipe_satker = st.selectbox(
            "Tipe Satker",
            ["Dekonsentrasi", "Kantor Daerah", "Kantor Pusat", "Tugas Pembantuan"],
        )

    if st.button("Prediksi", type="primary"):
        model = None
        model_error = None
        try:
            import Orange

            model = load_model()
        except FileNotFoundError as exc:
            model_error = f"Model belum tersedia: {exc}"
        except ImportError as exc:
            model_error = f"Dependensi model belum tersedia: {exc}"
        except (pickle.UnpicklingError, EOFError, AttributeError) as exc:
            model_error = f"Model gagal dimuat: {exc}"

        if model is None:
            st.error(model_error or "Model belum tersedia.")
        else:
            tipe_values = [
                "Dekonsentrasi",
                "Kantor Daerah",
                "Kantor Pusat",
                "Tugas Pembantuan",
            ]
            tipe_indicators = [
                1.0 if tipe_satker == tipe_value else 0.0
                for tipe_value in tipe_values
            ]
            input_row = [
                float(jumlah_spm),
                float(revisi_dipa),
                float(deviasi_rpd_persen),
                float(skor_ikpa),
                *tipe_indicators,
            ]

            try:
                table = Orange.data.Table.from_list(model.domain, [input_row])
                predictions = model(table)
                prediction_index = int(predictions[0])
                probabilities = model(table, model.Probs)[0]
                class_name = model.domain.class_var.values[prediction_index]
                confidence = float(probabilities[prediction_index])
            except (ValueError, TypeError, IndexError, AttributeError) as exc:
                st.error(f"Prediksi gagal dijalankan: {exc}")
            else:
                if class_name == "Ya":
                    st.success(
                        f"Prediksi: {class_name} "
                        f"(keyakinan {confidence:.1%})"
                    )
                else:
                    st.warning(
                        f"Prediksi: {class_name} "
                        f"(keyakinan {confidence:.1%})"
                    )

with tab_visualisasi:
    st.header("Visualisasi Bubble Plot")
    st.markdown(
        "Grafik bubble menunjukkan skor IKPA terhadap deviasi RPD, dengan warna berdasarkan kolom `realisasi_tercapai_95persen`."
    )

    chart = (
        alt.Chart(data)
        .mark_circle(opacity=0.7, size=100)
        .encode(
            x=alt.X(
                "skor_ikpa",
                title="Skor IKPA",
                scale=alt.Scale(domain=[70, 100]),
            ),
            y=alt.Y("deviasi_rpd_persen", title="Deviasi RPD (%)"),
            color=alt.Color(
                "realisasi_tercapai_95persen:N",
                title="Realisasi Tercapai 95%",
                scale=alt.Scale(
                    domain=["Tidak", "Ya"],
                    range=["red", "green"],
                ),
            ),
            tooltip=[
                "kode_satker",
                "tipe_satker",
                "skor_ikpa",
                "deviasi_rpd_persen",
                "realisasi_tercapai_95persen",
            ],
        )
        .properties(width=900, height=550)
        .interactive()
    )
    st.altair_chart(chart, width=900)

    st.subheader("Histogram Skor IKPA")
    histogram = (
        alt.Chart(data)
        .mark_bar()
        .encode(
            x=alt.X(
                "skor_ikpa:Q",
                bin=alt.Bin(maxbins=20),
                title="Skor IKPA",
            ),
            y=alt.Y("count():Q", title="Jumlah Satker"),
            tooltip=[alt.Tooltip("count():Q", title="Jumlah Satker")],
        )
        .properties(width=900, height=300)
    )
    st.altair_chart(histogram, width=900)

    st.subheader("Persentase Realisasi per Triwulan")
    pilihan_tampilan = st.radio(
        "Tampilan realisasi",
        ["Keseluruhan", "Per kementerian", "Bandingkan kementerian"],
        horizontal=True,
    )
    data_per_kementerian = [
        (nama, data[data["nama_kementerian"] == nama])
        for nama in sorted(data["nama_kementerian"].dropna().unique())
    ]
    if pilihan_tampilan == "Per kementerian":
        kementerian = st.selectbox(
            "Pilih kementerian",
            sorted(data["nama_kementerian"].dropna().unique()),
        )
        kelompok_data = [
            (kementerian, data[data["nama_kementerian"] == kementerian])
        ]
    elif pilihan_tampilan == "Bandingkan kementerian":
        kementerian_dipilih = st.multiselect(
            "Pilih maksimal 3 kementerian",
            options=[nama for nama, _ in data_per_kementerian],
            default=[nama for nama, _ in data_per_kementerian[:3]],
            max_selections=3,
        )
        kelompok_data = [
            (nama, data[data["nama_kementerian"] == nama])
            for nama in kementerian_dipilih
        ]
    else:
        kelompok_data = [("Keseluruhan", data)]

    kolom_triwulan = {
        "TW I": "realisasi_tw1_persen",
        "TW II": "realisasi_tw2_persen",
        "TW III": "realisasi_tw3_persen",
    }
    persentase_tertimbang = []
    for nama, data_realisasi in kelompok_data:
        for triwulan, kolom in kolom_triwulan.items():
            valid = data_realisasi[["pagu_miliar", kolom]].dropna()
            persentase_tertimbang.append(
                {
                    "kementerian": nama,
                    "triwulan": triwulan,
                    "persentase": (valid[kolom] * valid["pagu_miliar"]).sum()
                    / valid["pagu_miliar"].sum(),
                }
            )

    if persentase_tertimbang:
        data_grafik = pd.DataFrame(persentase_tertimbang)
        grafik_realisasi = (
            alt.Chart(data_grafik)
            .mark_line(point=True)
            .encode(
                x=alt.X(
                    "triwulan:N",
                    title="Triwulan",
                    sort=["TW I", "TW II", "TW III"],
                ),
                y=alt.Y("persentase:Q", title="Persentase Realisasi (%)"),
                tooltip=[
                    alt.Tooltip("kementerian:N", title="Kementerian"),
                    alt.Tooltip("triwulan:N", title="Triwulan"),
                    alt.Tooltip(
                        "persentase:Q",
                        title="Persentase Realisasi",
                        format=".2f",
                    ),
                ],
            )
        )
        if pilihan_tampilan == "Bandingkan kementerian":
            grafik_realisasi = grafik_realisasi.encode(
                color=alt.Color("kementerian:N", title="Kementerian"),
            )
        grafik_realisasi = grafik_realisasi.properties(
            width=900,
            height=350,
        )
        st.altair_chart(grafik_realisasi, width=900)
    else:
        st.info("Pilih setidaknya satu kementerian untuk menampilkan grafik.")

    st.caption(
        "Persentase tiap triwulan ditampilkan sesuai kolom sumber dan dirata-ratakan "
        "dengan bobot pagu; tidak dijumlahkan atau dihitung selisihnya."
    )

    st.subheader("Heatmap Korelasi")
    kolom_korelasi = [
        "pagu_miliar",
        "jumlah_pegawai",
        "jumlah_spm",
        "revisi_dipa",
        "realisasi_tw1_persen",
        "realisasi_tw2_persen",
        "realisasi_tw3_persen",
        "deviasi_rpd_persen",
        "skor_ikpa",
    ]
    metode_korelasi = st.selectbox(
        "Metode korelasi",
        ["Pearson", "Spearman"],
    )
    matriks_korelasi = data[kolom_korelasi].corr(
        method=metode_korelasi.lower(),
    )
    data_korelasi = (
        matriks_korelasi.rename_axis("variabel_y")
        .reset_index()
        .melt(
            id_vars="variabel_y",
            var_name="variabel_x",
            value_name="koefisien",
        )
    )
    sel_korelasi = (
        alt.Chart(data_korelasi)
        .mark_rect()
        .encode(
            x=alt.X(
                "variabel_x:N",
                title=None,
                sort=kolom_korelasi,
                axis=alt.Axis(labelAngle=-45),
            ),
            y=alt.Y(
                "variabel_y:N",
                title=None,
                sort=kolom_korelasi,
            ),
            color=alt.Color(
                "koefisien:Q",
                title="Koefisien",
                scale=alt.Scale(
                    domain=[-1, 1],
                    scheme="redblue",
                ),
            ),
            tooltip=[
                alt.Tooltip("variabel_y:N", title="Variabel"),
                alt.Tooltip("variabel_x:N", title="Dibandingkan dengan"),
                alt.Tooltip("koefisien:Q", title="Koefisien", format=".2f"),
            ],
        )
    )
    label_korelasi = (
        alt.Chart(data_korelasi)
        .mark_text(fontSize=10)
        .encode(
            x=alt.X("variabel_x:N", sort=kolom_korelasi),
            y=alt.Y("variabel_y:N", sort=kolom_korelasi),
            text=alt.Text("koefisien:Q", format=".2f"),
        )
    )
    heatmap = (sel_korelasi + label_korelasi).properties(
        width=750,
        height=650,
    )
    st.altair_chart(heatmap, width=900)
    st.caption(
        "Korelasi menunjukkan hubungan statistik antara variabel dan tidak "
        "membuktikan sebab-akibat. Kode satker dan label target tidak disertakan."
    )

    st.subheader("Total Pagu menurut Pengelompokan")
    opsi_pengelompokan = {
        "Nama Kementerian": "nama_kementerian",
        "Provinsi": "provinsi",
        "Jenis Belanja Utama": "jenis_belanja_utama",
    }
    pilihan_pengelompokan = st.selectbox(
        "Kelompokkan pagu berdasarkan",
        list(opsi_pengelompokan),
    )
    kolom_pengelompokan = opsi_pengelompokan[pilihan_pengelompokan]
    if kolom_pengelompokan == "jenis_belanja_utama":
        judul_pagu = "Pagu Satker menurut Jenis Belanja Utama"
    else:
        judul_pagu = f"Total Pagu menurut {pilihan_pengelompokan}"
    st.markdown(f"**{judul_pagu}**")

    data_pagu = data.dropna(subset=[kolom_pengelompokan, "pagu_miliar"])
    total_pagu_terfilter = data_pagu["pagu_miliar"].sum()
    if total_pagu_terfilter > 0:
        ringkasan_pagu = (
            data_pagu.groupby(kolom_pengelompokan, as_index=False)["pagu_miliar"]
            .sum()
            .rename(
                columns={
                    kolom_pengelompokan: "kelompok",
                    "pagu_miliar": "total_pagu",
                }
            )
        )
        ringkasan_pagu["persentase_total"] = (
            ringkasan_pagu["total_pagu"] / total_pagu_terfilter * 100
        )
        grafik_pagu = (
            alt.Chart(ringkasan_pagu)
            .mark_bar()
            .encode(
                x=alt.X("total_pagu:Q", title="Total Pagu (Rp miliar)"),
                y=alt.Y(
                    "kelompok:N",
                    title=None,
                    sort=alt.SortField(field="total_pagu", order="descending"),
                ),
                tooltip=[
                    alt.Tooltip(
                        "total_pagu:Q",
                        title="Total Pagu (Rp miliar)",
                        format=",.2f",
                    ),
                    alt.Tooltip(
                        "persentase_total:Q",
                        title="Persentase dari Total Pagu (%)",
                        format=".2f",
                    ),
                ],
            )
            .properties(
                width=900,
                height=max(300, len(ringkasan_pagu) * 30),
            )
        )
        st.altair_chart(grafik_pagu, width=900)
    else:
        st.info("Tidak ada total pagu untuk pengelompokan yang dipilih.")

    if kolom_pengelompokan == "jenis_belanja_utama":
        st.caption(
            "Grafik mengelompokkan total pagu satker menurut jenis belanja utama; "
            "grafik ini bukan rincian nominal setiap jenis belanja."
        )