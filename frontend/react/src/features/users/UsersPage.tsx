import React, { useEffect, useState } from "react";
import { Save, UserRound } from "lucide-react";
import { api, send } from "../../services/api";
import type { User } from "../../types";
import { Header, PanelTitle, Modal } from "../../components/Common";


export function UsersPage() {
    const [users, setUsers] = useState<User[]>([]);
    const [form, setForm] = useState({
        username: "",
        password: "",
        role: "viewer",
    });
    const [editing, setEditing] = useState<User | null>(null);
    const load = () => {
        api<User[]>("/api/v1/users")
            .then(setUsers)
            .catch(() => undefined);
    };
    useEffect(() => {
        load();
    }, []);
    const create = (e: React.FormEvent) => {
        e.preventDefault();
        send("/api/v1/users", form)
            .then(() => {
                setForm({ username: "", password: "", role: "viewer" });
                load();
            })
            .catch(() => alert("Não foi possível criar o usuário."));
    };
    const update = () =>
        editing &&
        api(`/api/v1/users/${editing.id}`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username: form.username, role: editing.role, password: form.password }),
        }).then(() => {
            setEditing(null);
            setForm({ ...form, password: "" });
            load();
        });
    return (
        <>
            <Header
                kicker="CONTROLE DE ACESSO"
                title="Usuários"
                description="Gerencie contas, papéis e senhas do sistema."
            />
            <div className="panel">
                <PanelTitle kicker="NOVO ACESSO" title="Adicionar usuário" />
                <form className="user-form" onSubmit={create}>
                    <input
                        placeholder="Nome de usuário"
                        required
                        value={form.username}
                        onChange={(e) => setForm({ ...form, username: e.target.value })}
                    />
                    <input
                        type="password"
                        placeholder="Senha"
                        required
                        value={form.password}
                        onChange={(e) => setForm({ ...form, password: e.target.value })}
                    />
                    <select
                        value={form.role}
                        onChange={(e) => setForm({ ...form, role: e.target.value })}
                    >
                        <option value="viewer">Viewer</option>
                        <option value="editor">Editor</option>
                        <option value="admin">Admin</option>
                    </select>
                    <button className="button primary">
                        <UserRound size={15} /> Criar usuário
                    </button>
                </form>
                <div className="table-scroll">
                    <table>
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Usuário</th>
                                <th>Papel</th>
                                <th>Criação</th>
                                <th>Ação</th>
                            </tr>
                        </thead>
                        <tbody>
                            {users.map((u) => (
                                <tr key={u.id}>
                                    <td>{u.id}</td>
                                    <td>
                                        <b>{u.username}</b>
                                    </td>
                                    <td>
                                        <span className="tag">{u.role}</span>
                                    </td>
                                    <td>{u.created_at || "-"}</td>
                                    <td>
                                        <button
                                            className="text-button"
                                            onClick={() => {
                                                setEditing(u);
                                                setForm({ ...form, username: u.username, password: "" });
                                            }}
                                        >
                                            Editar
                                        </button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
            {editing && (
                <Modal
                    title={`Editar ${editing.username}`}
                    close={() => setEditing(null)}
                >
                    <label>
                        Nome de usuário
                        <input value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} />
                    </label>
                    <label>
                        Papel
                        <select
                            value={editing.role}
                            onChange={(e) =>
                                setEditing({ ...editing, role: e.target.value as User["role"] })
                            }
                        >
                            <option value="viewer">Viewer</option>
                            <option value="editor">Editor</option>
                            <option value="admin">Admin</option>
                        </select>
                    </label>
                    <label>
                        Nova senha (opcional)
                        <input
                            type="password"
                            value={form.password}
                            onChange={(e) => setForm({ ...form, password: e.target.value })}
                        />
                    </label>
                    <button className="button primary" onClick={update}>
                        <Save size={15} /> Salvar
                    </button>
                </Modal>
            )}
        </>
    );
}
