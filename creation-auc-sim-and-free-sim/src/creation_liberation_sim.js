export async function creation_liberation_sim(payload) {
  const apiEndpoint = "http://10.2.145.60:5012/sim/creation-liberation";

  // 🔑 Récupérer le token depuis localStorage
  const token = localStorage.getItem('token');
  if (!token) {
    return { 
      success: false, 
      message: "Token d'authentification manquant.", 
      mode: payload.mode, 
      statusList: [], 
      resume: null 
    };
  }

  // 🔹 Récupérer username et user_type depuis localStorage
  const username = localStorage.getItem('username');
  const user_type = localStorage.getItem('userType');

  // 🔹 Ajouter ces infos dans le payload
  const payloadWithUser = {
    ...payload,
    username,
    user_type
  };
  console.log(payloadWithUser);
  try {
    const response = await fetch(apiEndpoint, {
      method: "POST",
      headers: { 
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}` // <-- important
      },
      body: JSON.stringify(payloadWithUser), // <-- envoyer payload enrichi
    });

    let data;
    try {
      data = await response.json();
    } catch (err) {
      const txt = await response.text();
      throw new Error(txt || "Réponse API non JSON");
    }

    if (!response.ok) {
      return {
        success: false,
        message: data.message || "Erreur serveur",
        mode: payload.mode,
        statusList: data.results || data.statusList || data.errors || [],
        resume: data.resume || null,
      };
    }

    const statusList = data.results || data.statusList || data.errors || [];
    const resume = data.resume || null;
    const message = data.message || (resume ? resume : null);

    return {
      success: data.success !== undefined ? data.success : true,
      message,
      mode: payload.mode,
      statusList,
      resume,
    };

  } catch (error) {
    console.error("Erreur API:", error);
    return {
      success: false,
      message: error.message || "Impossible de contacter le serveur.",
      mode: payload.mode,
      statusList: [],
      resume: null,
    };
  }
}
