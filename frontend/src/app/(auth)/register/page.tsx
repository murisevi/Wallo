'use client';

import { useState, type FormEvent } from 'react';
import Link from 'next/link';
import { useAuth } from '@/providers/auth-provider';
import { api, ApiError } from '@/lib/api';
import type { User } from '@/types';

export default function RegisterPage() {
  const { login } = useAuth();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await api.post<User>('/auth/register', { email, name, password });
      await login(email, password);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError('Ha ocurrido un error inesperado');
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-full flex-1 flex-col items-center justify-center px-6 py-16 bg-[#faf9f8]">
      <div className="w-full max-w-md rounded-3xl bg-white p-10 shadow-[0_20px_40px_rgba(48,51,51,0.08)]">
        {/* Logo */}
        <div className="mb-8 text-center">
          <p className="text-3xl font-extrabold tracking-tight text-[#0060ad]">Wallo</p>
          <p className="mt-1 text-sm text-[#5d605f]">Tus finanzas, bajo control.</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          {error && (
            <div className="rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
          )}

          <div>
            <label htmlFor="name" className="block text-sm font-semibold text-[#303333] mb-1.5">
              Nombre completo
            </label>
            <input
              id="name"
              type="text"
              required
              autoComplete="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="block w-full rounded-xl bg-[#f3f4f3] px-4 py-3 text-sm text-[#303333] placeholder:text-[#5d605f]/60 outline-none ring-1 ring-transparent focus:ring-2 focus:ring-[#0060ad]/20 transition-all"
              placeholder="Tu nombre"
            />
          </div>

          <div>
            <label htmlFor="email" className="block text-sm font-semibold text-[#303333] mb-1.5">
              Correo electrónico
            </label>
            <input
              id="email"
              type="email"
              required
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="block w-full rounded-xl bg-[#f3f4f3] px-4 py-3 text-sm text-[#303333] placeholder:text-[#5d605f]/60 outline-none ring-1 ring-transparent focus:ring-2 focus:ring-[#0060ad]/20 transition-all"
              placeholder="tu@email.com"
            />
          </div>

          <div>
            <label htmlFor="password" className="block text-sm font-semibold text-[#303333] mb-1.5">
              Contraseña
            </label>
            <input
              id="password"
              type="password"
              required
              autoComplete="new-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="block w-full rounded-xl bg-[#f3f4f3] px-4 py-3 text-sm text-[#303333] placeholder:text-[#5d605f]/60 outline-none ring-1 ring-transparent focus:ring-2 focus:ring-[#0060ad]/20 transition-all"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="mt-2 w-full rounded-full bg-gradient-to-r from-[#0060ad] to-[#68abff] px-4 py-3 text-sm font-bold text-white shadow-sm hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
          >
            {loading ? 'Creando cuenta…' : 'Crear cuenta'}
          </button>
        </form>

        <p className="mt-8 text-center text-sm text-[#5d605f]">
          ¿Ya tienes cuenta?{' '}
          <Link href="/login" className="font-semibold text-[#0060ad] hover:text-[#68abff] transition-colors">
            Inicia sesión
          </Link>
        </p>
      </div>
    </div>
  );
}
